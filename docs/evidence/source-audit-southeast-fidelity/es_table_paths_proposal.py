"""Proposed elimination of nested SAME-COLOR text-line background rectangles.

This changes only table detection input, never page drawing/rendering or text.
A short borderless fill fully nested with horizontal insets inside a larger
same-color opaque background cannot be an independent physical cell border.
All white rules and original full-cell backgrounds remain in the path list.
"""
def table_paths_without_nested_text_backgrounds(page,max_nested_height=22):
 paths=page.get_drawings();fills=[]
 for index,p in enumerate(paths):
  if p.get('type')!='f'or p.get('fill_opacity')!=1 or p.get('fill')is None:continue
  for item in p['items']:
   if item[0]=='re':fills.append((index,item[1],tuple(p['fill'])))
 removed=[]
 for i,r,color in fills:
  if len(paths[i]['items'])!=1:continue
  if not(3<r.height<max_nested_height and r.width>30):continue
  parent=next(((j,b)for j,b,c in fills if j!=i and c==color and b.x0<=r.x0+.1 and b.y0<=r.y0+.1 and b.x1>=r.x1-.1 and b.y1>=r.y1-.1 and ((b.width-r.width>=4 and b.height-r.height>=2)or(b.width-r.width>=-.2 and b.height-r.height>=40))),None)
  if parent:removed.append({'index':i,'seqno':paths[i]['seqno'],'bbox':list(r),'color':color,'parent_index':parent[0],'parent_bbox':list(parent[1]),'reason':'Opaque borderless text-line background nested with horizontal inset in same-color full-cell fill.'})
 indices={r['index']for r in removed};return[p for i,p in enumerate(paths)if i not in indices],removed
