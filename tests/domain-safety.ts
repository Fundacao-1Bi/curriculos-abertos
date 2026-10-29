export function testDatabaseName(connection:string|undefined):string {
 if(!connection)throw Error('Isolated test database URL required.');
 let parsed:URL;try{parsed=new URL(connection);}catch{throw Error('Invalid isolated test database URL.');}
 const name=decodeURIComponent(parsed.pathname.slice(1));
 if(!['postgres:','postgresql:'].includes(parsed.protocol)||!/^curriculum_test(?:_[a-f0-9]{12})?$/.test(name))throw Error('Refusing destructive test setup outside an owned curriculum_test database.');
 return name;
}
