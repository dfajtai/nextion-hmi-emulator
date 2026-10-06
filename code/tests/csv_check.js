const fs=require('fs');const path=require('path');
const [dataPath,corePath,toolsPath,statsCsv,seriesCsv]=process.argv.slice(2);
const DATA=new Function(fs.readFileSync(dataPath,'utf8')+';return DATA;')();
const {createCore}=require(path.resolve(corePath));const T=require(path.resolve(toolsPath));
const env={variables:DATA.variables,scale:ref=>{const m=/^([^.]+)\.([^.]+)\./.exec(ref);const pg=DATA.pages.find(p=>p.name===m[1]);const c=pg&&pg.comps.find(c=>c.objname===m[2]);return c&&c.type===59?Math.pow(10,c.vvs1||0):1;}};
const out={};
let t=T.parseCSV(fs.readFileSync(statsCsv,'utf8'));
const prof=DATA.csvProfiles.stats;
const sc=T.buildStatsScenario(t,{column:'suly_g',groupColumn:'csoport',profile:prof,waitMs:500},env);
const core=createCore(DATA,{log(){}, render(){}, changed(){}});
const r=core.runScenarioSync(sc);
out.stats={groups:sc.description,steps:r.steps,problems:r.problems,scnErr:core.stats.scenarioErrors.map(e=>e.msg),
  mean:core.S()['pageStat1']['xmean'].val, n:core.S()['pageStat1']['xquantity'].val, sd:core.S()['pageStat1']['xsd'].val, grp:core.S()['pageStat1']['t6'].txt,
  wave:(core.S()['pageStat2']['s0']['@wave']||[[]])[0].length};
let t2=T.parseCSV(fs.readFileSync(seriesCsv,'utf8'));
const sc2=T.buildSeriesScenario(t2,{},env);
const core2=createCore(DATA,{log(){},render(){},changed(){}});
const r2=core2.runScenarioSync(sc2);
out.series={cols:sc2.description,unknown:sc2.unknownColumns,steps:r2.steps,problems:r2.problems,scnErr:core2.stats.scenarioErrors.map(e=>e.msg),ms:r2.simulatedMs,
  charge:core2.S()['pageMainAuto']['charge_level'].val,weight:core2.S()['pageMainAuto']['weight'].val,warn:t2.warnings};
out.parse={semi:T.parseCSV('a;b\n1,5;2').rows[0],tab:T.parseCSV('a\tb\n1\t2').delimiter,quoted:T.parseCSV('a,b\n"x,y",2').rows[0],bom:T.parseCSV('\uFEFFa,b\n1,2').header};
out.names={stats:sc.name,series:sc2.name};
out.num=[T.toNumber('1,5',';'),T.toNumber('1.5',','),T.toNumber('abc',',')];
const s=T.stats([2,4,4,4,5,5,7,9]);out.sd=[s.n,s.mean,Math.round(s.sd*1000)/1000];
console.log(JSON.stringify(out));
