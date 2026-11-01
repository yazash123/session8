/* A stand-in for the Firebase compat SDK, for tools/check.py only. One shared "database" kept by
   check.py's little server (/__fakefs), so separate browsers see each other's writes (polled).
   Counts listener reads in window.__reads, the way Firestore bills them. */
(function(){
  var KEY='fakefs', subs=[], uid=0;
  window.__reads=0; window.__listeners={};
  function xhr(m,body){var x=new XMLHttpRequest();x.open(m,'/__fakefs',false);x.send(body||null);return x.responseText;}
  function load(){try{return JSON.parse(xhr('GET')||'{}');}catch(e){return {};}}
  function store(db){xhr('POST',JSON.stringify(db));fire();}
  function fire(){subs.slice().forEach(function(s){s.check();});}
  setInterval(function(){if(subs.length)fire();},200);
  window.__fakeload=load;
  function snapDoc(path,db){var d=db[path];return {id:path.split('/').pop(),exists:!!d,data:function(){return d?JSON.parse(JSON.stringify(d)):undefined;}};}
  function listen(kind,path,next){
    var last=null, live=true, name=kind+':'+path;
    window.__listeners[name]=(window.__listeners[name]||0)+1;
    var s={check:function(){if(!live)return;var db=load(),cur;
      if(kind==='doc'){cur=JSON.stringify(db[path]||null);if(cur===last)return;window.__reads+=1;last=cur;next(snapDoc(path,db));}
      else{var docs=Object.keys(db).filter(function(k){return k.indexOf(path+'/')===0&&k.split('/').length===2;}).sort();
        cur=JSON.stringify(docs.map(function(k){return [k,db[k]];}));if(cur===last)return;
        var prev=last?JSON.parse(last):[],pm={};prev.forEach(function(p){pm[p[0]]=JSON.stringify(p[1]);});
        var changed=docs.filter(function(k){return pm[k]!==JSON.stringify(db[k]);}).length;
        window.__reads+=Math.max(1,last?changed:docs.length);last=cur;
        next({docs:docs.map(function(k){return snapDoc(k,db);})});}}};
    subs.push(s); setTimeout(s.check,0);
    return function(){live=false;window.__listeners[name]--;subs=subs.filter(function(x){return x!==s;});};
  }
  function docRef(path){return {id:path.split('/').pop(),path:path,
    set:function(d){var db=load();db[path]=JSON.parse(JSON.stringify(d));store(db);return Promise.resolve();},
    update:function(d){var db=load();if(!db[path])return Promise.reject(new Error('not-found'));Object.keys(d).forEach(function(k){db[path][k]=d[k];});store(db);return Promise.resolve();},
    delete:function(){var db=load();delete db[path];store(db);return Promise.resolve();},
    get:function(){window.__reads++;return Promise.resolve(snapDoc(path,load()));},
    onSnapshot:function(n,e){return listen('doc',path,n);}};}
  var fs={settings:function(){},doc:docRef,collection:function(n){return {doc:function(id){return docRef(n+'/'+(id||('x'+(++uid)+Date.now())));},onSnapshot:function(nx,e){return listen('col',n,nx);}};}};
  var user=null,authFns=[];
  var auth={signInWithEmailAndPassword:function(em,pw){if(pw==='testpass1'){user={email:em};authFns.forEach(function(f){f(user);});return Promise.resolve({user:user});}return Promise.reject({code:'auth/wrong-password'});},
    onAuthStateChanged:function(f){authFns.push(f);setTimeout(function(){f(user);},0);}};
  window.firebase={apps:[],initializeApp:function(c){this.apps.push(c);return {};},app:function(){return {};},firestore:function(){return fs;},auth:function(){return auth;}};
})();
