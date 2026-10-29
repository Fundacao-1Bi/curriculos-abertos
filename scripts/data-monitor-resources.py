#!/usr/bin/env python3
"""Observe batch memory/disk without loading extraction JSON or changing jobs."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--job-id',required=True);parser.add_argument('--interval',type=int,default=10);parser.add_argument('--minimum-free-gib',type=float,default=5);args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',args.job_id):raise ValueError('Invalid job identity')
    interval=max(5,args.interval);output=ROOT/'var/jobs'/f'{args.job_id}-resources.json';samples=output.with_suffix('.jsonl');started=datetime.datetime.now(datetime.timezone.utc).isoformat();peak=0;min_free=None;count=0
    while True:
        observed=[];processes={};selected=set()
        raw=subprocess.check_output(['ps','-axo','pid=,ppid=,rss=,command='],text=True)
        for line in raw.splitlines():
            fields=line.strip().split(None,3)
            if len(fields)!=4:continue
            pid,ppid,rss,command=fields
            processes[int(pid)]={'pid':int(pid),'parent_pid':int(ppid),'rss_bytes':int(rss)*1024}
            if 'pipeline/batch.py' in command and args.job_id in command:selected.add(int(pid))
        # macOS spawn workers have multiprocessing argv, not the original job
        # arguments. Follow descendants instead of omitting worker memory.
        while True:
            children={pid for pid,process in processes.items() if process['parent_pid'] in selected}
            expanded=selected|children
            if expanded==selected:break
            selected=expanded
        observed=[processes[pid] for pid in sorted(selected)]
        disk=shutil.disk_usage(ROOT);total=sum(p['rss_bytes'] for p in observed);peak=max(peak,total);min_free=disk.free if min_free is None else min(min_free,disk.free);count+=1
        checkpoint=ROOT/'var/jobs'/f'{args.job_id}.json'
        job=json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
        sample={'method_version':'batch-descendant-rss-v2','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'processes':observed,'observed_batch_rss_bytes':total,'disk_free_bytes':disk.free,'load_average':list(os.getloadavg()),'job_state':job.get('state'),'sources_completed':len(job.get('results',[])),'sources_expected':job.get('sources_expected')}
        with samples.open('a') as stream:stream.write(json.dumps(sample,sort_keys=True)+'\n')
        summary={'job_id':args.job_id,'started_at':started,'updated_at':sample['at'],'samples':count,'sample_interval_seconds':interval,'observed_peak_aggregate_rss_bytes':peak,'minimum_observed_disk_free_bytes':min_free,'latest':sample,'method':'Read-only ps RSS samples of batch parent/workers and filesystem disk_usage. Observed aggregate peak is sampled, not kernel high-water RSS; no all-cache loading or stress benchmark.'}
        temp=output.with_suffix('.json.tmp');temp.write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n');temp.replace(output)
        if not observed:return 0
        if disk.free<args.minimum_free_gib*1024**3:
            # Reversible suspension preserves in-flight native parsing/temporary
            # files and the already atomic per-source checkpoint, unlike killing
            # workers and pretending that their unfinished sources completed.
            suspended=[]
            for pid in sorted(selected):
                try:os.kill(pid,signal.SIGSTOP);suspended.append(pid)
                except ProcessLookupError:pass
            pause={'job_id':args.job_id,'at':sample['at'],'reason':'Disk guard reached reserved pre-consolidation margin','minimum_free_gib':args.minimum_free_gib,'observed_free_bytes':disk.free,'suspended_pids':suspended,'signal':'SIGSTOP','job_checkpoint':str(checkpoint.relative_to(ROOT)),'sources_completed':sample['sources_completed'],'resume':'After verifying free space and unchanged parser, send SIGCONT only to these still-matching batch PIDs. No data or caches were deleted.'}
            pause_path=ROOT/'var/jobs'/f'{args.job_id}-resource-pause.json';pause_path.write_text(json.dumps(pause,sort_keys=True,indent=2)+'\n')
            print(json.dumps(pause),flush=True)
            return 75
        time.sleep(interval)


if __name__=='__main__':raise SystemExit(main())
