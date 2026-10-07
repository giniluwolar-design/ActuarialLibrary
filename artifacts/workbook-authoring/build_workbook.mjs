// Authoring-only dependency: @oai/artifact-tool. End users need only the resulting .xlsx.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const data=JSON.parse(await fs.readFile(path.join(root,'artifacts/workbook_payload.json'),'utf8'));
const wb=Workbook.create();
const names=['Summary','Assumptions','Paid','Incurred','Counts','Severity','BF','Checks','Data','Sources'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const fmt='#,##0.00;(#,##0.00);"–"';
const col=n=>{let s='';for(;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s};
const val=(s,r,c,v)=>s.getCell(r-1,c-1).values=[[v]];
const fx=(s,r,c,f)=>s.getCell(r-1,c-1).formulas=[[f]];
function header(s,row,columns,start=3){
 s.getRangeByIndexes(row-1,start-1,1,columns.length).values=[columns];
 s.getRangeByIndexes(row-1,start-1,1,columns.length).format={fill:'#243c49',font:{color:'#ffffff',bold:true},rowHeight:34,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
}
function note(s,row,text){val(s,row,3,text);s.getRangeByIndexes(row-1,2,1,1).format.font={italic:true,color:'#586870'};}
function input(s,range){s.getRange(range).format.fill='#fff4d5';s.getRange(range).format.font.color='#1757aa';}
for(const [name,s] of Object.entries(sheets)){
 s.showGridLines=false;
 s.getRange('A1:AD160').format.font={name:'Arial',size:10,color:'#18282f'};
 s.getRange('A1:B160').format.columnWidth=2.5;
 s.getRange('C1:C160').format.columnWidth=15;
 s.getRange('D1:AD160').format.columnWidth=15;
 s.getRange('C1:AD160').format.rowHeight=21;
 s.getRange('D7:AD155').setNumberFormat(fmt);
 s.getRange('D7:AD155').format.horizontalAlignment='right';
 val(s,2,3,name==='Summary'?'Claims reserving — worked example':name);
 s.getRange('C2').format.font={size:15,bold:true};
 if(!['Assumptions','Data','Sources'].includes(name)){
  val(s,4,3,'Active portfolio');fx(s,4,5,"='Assumptions'!E4");s.getRange('E4').format.font.color='#287451';
 }
 if(['Paid','Incurred','Counts','Data'].includes(name))s.freezePanes.freezeRows(name==='Data'?1:6);
}
sheets.Summary.tabColor='#243c49';sheets.Assumptions.tabColor='#71828b';

// One authoritative assumptions area.
const a=sheets.Assumptions;
const settings=[['Active portfolio','Motor'],['Valuation',new Date('2025-12-31T00:00:00Z')],
 ['',''],['Severity average','weighted'],['Annual severity trend',0],['Historical years',10],
 ['Target count mode','developed'],['No further reporting','No']];
settings.forEach(([k,v],i)=>{val(a,i+4,3,k);val(a,i+4,5,v)});
a.getRange('C4:C11').format.columnWidth=29;
a.getRange('E5').setNumberFormat('dd-mmm-yyyy');a.getRange('E8').setNumberFormat('0.0%');
input(a,'E4');input(a,'E7:E11');
a.getRange('E9').setNumberFormat('0');
a.getRange('E4').dataValidation={rule:{type:'list',values:['Motor','Liability']}};
a.getRange('E7').dataValidation={rule:{type:'list',values:['weighted','simple']}};
a.getRange('E10').dataValidation={rule:{type:'list',values:['developed','manual','exposure','reported']}};
a.getRange('E11').dataValidation={rule:{type:'list',values:['No','Yes']}};
header(a,14,['Basis','Factor average','Pair window (0=all)','Tail factor','Rationale']);
for(let i=0;i<3;i++){
 a.getRangeByIndexes(14+i,2,1,5).values=[[['Paid','Incurred','Counts'][i],'volume',0,1,'']];
 a.getRange(`D${15+i}`).dataValidation={rule:{type:'list',values:['volume','simple']}};
}
input(a,'D15:G17');a.getRange('F15:F17').setNumberFormat('0.0000');
a.getRange('E15:E17').setNumberFormat('0');
note(a,19,'Amber cells are editable. Blank overrides use the calculation; zero priors/counts are real values.');
header(a,21,['Origin','BF prior','Expected count','Exposure','Frequency','Historical ultimate','Historical count','Selected method','Manual ultimate','Selection note','Include in history']);
for(let i=0;i<20;i++)a.getRange(`C${22+i}:M${22+i}`).values=[[2006+i,null,null,null,null,null,null,'',null,'',1]];
input(a,'D22:M41');a.getRange('G22:G41').setNumberFormat('0.0000');a.getRange('M22:M41').setNumberFormat('0');
a.getRange('J22:J41').format.columnWidth=24;a.getRange('L22:L41').format.columnWidth=35;
a.getRange('J22:J41').dataValidation={rule:{type:'list',values:['paid_cl','incurred_cl','paid_bf','incurred_bf','frequency_severity','manual']}};
a.getRange('M22:M41').dataValidation={rule:{type:'list',values:['0','1']}};
note(a,44,'Historical selections affect calibration only. Final method choices never feed historical calibration.');
note(a,46,'Fixed example: annual 2006–2025, EUR, after deductible. The valuation is descriptive, not an editable date filter.');
note(a,48,'Deductible is a source field only. No amount is automatically deducted.');

// All annual claim snapshots. Only incurred is derived; historical values stay intact.
const raw=sheets.Data;
raw.getRange('A1:AD160').clear({applyTo:'all'});raw.showGridLines=false;
header(raw,1,[...data.columns,'incurred'],1);
const rawRows=data.rows.map(r=>r.map((v,i)=>[2,3,4].includes(i)?new Date(v+'T00:00:00Z'):v));
raw.getRangeByIndexes(1,0,rawRows.length,13).values=rawRows;
raw.getRange(`N2:N${rawRows.length+1}`).formulas=rawRows.map((_,i)=>[`=G${i+2}+H${i+2}`]);
raw.getRange(`A1:N${rawRows.length+1}`).format.font={name:'Arial',size:10};
raw.getRange(`A1:N${rawRows.length+1}`).format.rowHeight=18;
raw.getRange('A1:N1').format.font={bold:true,color:'#ffffff'};
raw.getRange(`C2:E${rawRows.length+1}`).setNumberFormat('dd-mmm-yyyy');
raw.getRange(`G2:I${rawRows.length+1}`).setNumberFormat(fmt);raw.getRange(`N2:N${rawRows.length+1}`).setNumberFormat(fmt);
raw.getRange(`A1:N${rawRows.length+1}`).format.columnWidth=18;
raw.getRange(`K1:K${rawRows.length+1}`).format.columnWidth=23;
const groups={};
data.rows.forEach((r,i)=>{const key=[r[0],r[11],r[12]].join(':');if(!groups[key])groups[key]=[i+2,i+2];else groups[key][1]=i+2});
function sourceSum(p,year,valuation,basis){
 const span=groups[[p,year,valuation].join(':')];
 if(!span)return '0';
 if(basis==='Counts')return `COUNTA('Data'!B${span[0]}:B${span[1]})`;
 const c=basis==='Paid'?'G':'N';return `SUM('Data'!${c}${span[0]}:${c}${span[1]})`;
}

for(const [bi,name] of ['Paid','Incurred','Counts'].entries()){
 const s=sheets[name], ar=15+bi;
 header(s,6,['Origin',...Array.from({length:20},(_,i)=>i+1)]);
 header(s,6,['Origin','Latest','CDF','CL ultimate'],25);
 header(s,31,['Age','Volume factor','Simple factor','Override','Selected','CDF','Pairs','Override reason','Numerator','Denominator']);
 note(s,55,'Factor exclusions below: 1 = exclude. Enter a reason beside a selected factor or in Assumptions.');
 header(s,58,['Exclude pair',...Array.from({length:19},(_,i)=>i+1)]);
 note(s,81,'Individual link ratios: invalid starting balances are represented by zero only in these calculation helpers.');
 header(s,83,['Link ratio',...Array.from({length:19},(_,i)=>i+1)]);
 header(s,108,['Eligible pair',...Array.from({length:19},(_,i)=>i+1)]);
 header(s,133,['Selected pair',...Array.from({length:19},(_,i)=>i+1)]);
 for(let i=0;i<20;i++){
  const r=7+i;val(s,r,3,2006+i);val(s,r,25,2006+i);
  for(const base of [59,84,109,134])val(s,base+i,3,2006+i);
  for(let j=0;j<20;j++){
   const cc=col(4+j);
   if(i+j<20)fx(s,r,4+j,`=IF('Assumptions'!$E$4="Motor",${sourceSum('Motor',2006+i,2006+i+j,name)},${sourceSum('Liability',2006+i,2006+i+j,name)})`);
   if(j<19){
    val(s,59+i,4+j,0);
    fx(s,84+i,4+j,i+j<19?`=IF(${cc}${r}>0,${col(5+j)}${r}/${cc}${r},0)`:'=0');
    fx(s,109+i,4+j,i+j<19?`=IF(AND(${cc}${r}>0,${cc}${59+i}=0),1,0)`:'=0');
    fx(s,134+i,4+j,`=IF(AND(${cc}${109+i}=1,OR('Assumptions'!$E$${ar}=0,SUM(${cc}${109+i}:${cc}$128)<='Assumptions'!$E$${ar})),1,0)`);
   }
  }
  fx(s,r,26,`=${col(23-i)}${r}`);fx(s,r,27,`=H${51-i}`);
  fx(s,r,28,`=IF(AND(ISNUMBER(Z${r}),ISNUMBER(AA${r})),Z${r}*AA${r},"n.a.")`);
 }
 input(s,'D59:V78');s.getRange('D59:V78').setNumberFormat('0');
 s.getRange('D59:V78').dataValidation={rule:{type:'list',values:['0','1']}};
 s.getRange('D84:V103').setNumberFormat('0.0000');s.getRange('D109:V153').setNumberFormat('0');
 for(let j=0;j<19;j++){
  const r=32+j, cc=col(4+j),next=col(5+j);val(s,r,3,j+1);
  fx(s,r,11,`=SUMPRODUCT(${next}7:${next}26,${cc}134:${cc}153)`);
  fx(s,r,12,`=SUMPRODUCT(${cc}7:${cc}26,${cc}134:${cc}153)`);
  fx(s,r,9,`=SUM(${cc}134:${cc}153)`);
  fx(s,r,4,`=IF(L${r}>0,K${r}/L${r},"n.a.")`);
  fx(s,r,5,`=IF(I${r}>0,SUMPRODUCT(${cc}84:${cc}103,${cc}134:${cc}153)/I${r},"n.a.")`);
  fx(s,r,7,`=IF(ISNUMBER(F${r}),IF(F${r}>0,F${r},"n.a."),IF('Assumptions'!$D$${ar}="volume",D${r},E${r}))`);
  fx(s,r,8,`=IF(AND(ISNUMBER(G${r}),ISNUMBER(H${r+1})),G${r}*H${r+1},"n.a.")`);
 }
 val(s,51,3,20);fx(s,51,7,`='Assumptions'!F${ar}`);fx(s,51,8,'=G51');val(s,51,10,'Tail');
 input(s,'F32:F50');input(s,'J32:J50');s.getRange('D32:H51').setNumberFormat('0.000000');
 s.getRange('I32:I51').setNumberFormat('0');s.getRange('J32:J50').format.columnWidth=29;
 if(name==='Counts')s.getRange('D7:W26').setNumberFormat('0');
}

const sev=sheets.Severity;
header(sev,6,['Origin','Historical ultimate','Historical count','Target count','Severity','Expected ultimate','Calibration years']);
header(sev,34,['Target year',...Array.from({length:20},(_,i)=>2006+i)]);
note(sev,32,'Trended severity by historical year. Only selected years before the target year are eligible.');
header(sev,59,['Claim weights',...Array.from({length:20},(_,i)=>2006+i)]);
for(let i=0;i<20;i++){
 const r=7+i,ar=22+i;val(sev,r,3,2006+i);val(sev,35+i,3,2006+i);val(sev,60+i,3,2006+i);
 fx(sev,r,4,`=IF(ISNUMBER('Assumptions'!H${ar}),'Assumptions'!H${ar},'Incurred'!AB${r})`);
 fx(sev,r,5,`=IF(ISNUMBER('Assumptions'!I${ar}),'Assumptions'!I${ar},'Counts'!AB${r})`);
 fx(sev,r,6,`=IF('Assumptions'!$E$10="developed",'Counts'!AB${r},IF('Assumptions'!$E$10="manual",IF(ISNUMBER('Assumptions'!E${ar}),'Assumptions'!E${ar},"n.a."),IF('Assumptions'!$E$10="exposure",IF(AND(ISNUMBER('Assumptions'!F${ar}),ISNUMBER('Assumptions'!G${ar})),'Assumptions'!F${ar}*'Assumptions'!G${ar},"n.a."),IF('Assumptions'!$E$11="Yes",'Counts'!Z${r},"n.a."))))`);
 for(let j=0;j<20;j++){
  const h=7+j,ah=22+j,c=col(4+j);
  const eligible=`AND(${c}$34<$C${35+i},${c}$34>=$C${35+i}-'Assumptions'!$E$9,'Assumptions'!$M$${ah}=1)`;
  fx(sev,35+i,4+j,`=IF(${eligible},IF(AND(ISNUMBER($D$${h}),ISNUMBER($E$${h}),$E$${h}>0),$D$${h}/$E$${h}*(1+'Assumptions'!$E$8)^($C${35+i}-${c}$34),"n.a."),"")`);
  fx(sev,60+i,4+j,`=IF(${eligible},IF(ISNUMBER($E$${h}),$E$${h},"n.a."),"")`);
 }
 fx(sev,r,7,`=IF(OR(COUNTIFS(D${35+i}:W${35+i},"n.a.")>0,COUNT(D${35+i}:W${35+i})=0),"n.a.",IF('Assumptions'!$E$7="weighted",IF(SUM(D${60+i}:W${60+i})>0,SUMPRODUCT(D${35+i}:W${35+i},D${60+i}:W${60+i})/SUM(D${60+i}:W${60+i}),"n.a."),AVERAGE(D${35+i}:W${35+i})))`);
 fx(sev,r,8,`=IF(AND(ISNUMBER(F${r}),ISNUMBER(G${r})),F${r}*G${r},"n.a.")`);
 fx(sev,r,9,`=COUNT(D${35+i}:W${35+i})`);
}

const bf=sheets.BF;
header(bf,6,['Origin','Prior ultimate','Paid','Paid CDF','Unpaid share','Paid BF ultimate','Incurred','Incurred CDF','Unreported share','Incurred BF ultimate']);
for(let i=0;i<20;i++){
 const r=7+i,ar=22+i;val(bf,r,3,2006+i);
 fx(bf,r,4,`=IF(ISNUMBER('Assumptions'!D${ar}),'Assumptions'!D${ar},'Severity'!H${r})`);
 fx(bf,r,5,`='Paid'!Z${r}`);fx(bf,r,6,`='Paid'!AA${r}`);
 fx(bf,r,7,`=IF(ISNUMBER(F${r}),IF(F${r}>=1,1-1/F${r},"n.a."),"n.a.")`);
 fx(bf,r,8,`=IF(AND(ISNUMBER(D${r}),ISNUMBER(G${r})),E${r}+D${r}*G${r},"n.a.")`);
 fx(bf,r,9,`='Incurred'!Z${r}`);fx(bf,r,10,`='Incurred'!AA${r}`);
 fx(bf,r,11,`=IF(ISNUMBER(J${r}),IF(J${r}>=1,1-1/J${r},"n.a."),"n.a.")`);
 fx(bf,r,12,`=IF(AND(ISNUMBER(D${r}),ISNUMBER(K${r})),I${r}+D${r}*K${r},"n.a.")`);
}
bf.getRange('G7:G26').setNumberFormat('0.0%');bf.getRange('K7:K26').setNumberFormat('0.0%');
bf.getRange('F7:F26').setNumberFormat('0.0000');bf.getRange('J7:J26').setNumberFormat('0.0000');
sev.getRange('I7:I26').setNumberFormat('0');
note(bf,30,'BF uses observed amounts plus expected remaining amounts. Invalid CDFs or missing priors give n.a.');

const sum=sheets.Summary;
header(sum,6,['Origin','Paid','Incurred','Paid CL','Incurred CL','Frequency × severity','Paid BF','Incurred BF','Selected ultimate','Outstanding','Additional reserve','Case reserves']);
for(let i=0;i<20;i++){
 const r=7+i,ar=22+i;val(sum,r,3,2006+i);
 for(const [c,ref] of [[4,`Paid!Z${r}`],[5,`Incurred!Z${r}`],[6,`Paid!AB${r}`],[7,`Incurred!AB${r}`],[8,`Severity!H${r}`],[9,`BF!H${r}`],[10,`BF!L${r}`]])fx(sum,r,c,'='+ref);
 fx(sum,r,11,`=IF('Assumptions'!J${ar}="paid_cl",F${r},IF('Assumptions'!J${ar}="incurred_cl",G${r},IF('Assumptions'!J${ar}="frequency_severity",H${r},IF('Assumptions'!J${ar}="paid_bf",I${r},IF('Assumptions'!J${ar}="incurred_bf",J${r},IF(AND('Assumptions'!J${ar}="manual",ISNUMBER('Assumptions'!K${ar}),'Assumptions'!L${ar}<>""),'Assumptions'!K${ar},"n.a."))))))`);
 fx(sum,r,12,`=IF(ISNUMBER(K${r}),K${r}-D${r},"n.a.")`);
 fx(sum,r,13,`=IF(ISNUMBER(K${r}),K${r}-E${r},"n.a.")`);fx(sum,r,14,`=E${r}-D${r}`);
}
val(sum,28,3,'Total');for(let c=4;c<=14;c++)fx(sum,28,c,`=IF(COUNT(${col(c)}7:${col(c)}26)=20,SUM(${col(c)}7:${col(c)}26),"n.a.")`);
sum.getRange('C28:N28').format.font.bold=true;
note(sum,31,'Select a final method per origin in Assumptions. An incomplete selection is never presented as a full reserve.');
note(sum,33,'Outstanding = ultimate − paid. Additional reserve = ultimate − incurred (IBNR + IBNER).');
note(sum,35,'n.a. means unavailable: inspect factor availability, historical calibration, expected count or prior.');
note(sum,37,'Read the methodology and limits in Sources. No discounting, stochastic intervals or automatic method choice.');
for(const c of ['L','M'])sum.getRange(`${c}7:${c}26`).conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{fill:'#fce4df',font:{color:'#9c3023'}}});

const check=sheets.Checks;
header(check,6,['Origin','Paid CL difference','Incurred CL difference','FS difference','Paid BF difference','Incurred BF difference','Reserve identity']);
const checkMethods=['paid_cl','incurred_cl','frequency_severity','paid_bf','incurred_bf'];
header(check,33,['Portfolio','Origin',...checkMethods]);
const expectedRows=[];
for(const p of ['Motor','Liability'])for(let i=0;i<20;i++)expectedRows.push([p,2006+i,...checkMethods.map(m=>data.expected[p].base.find(r=>r.origin===String(2006+i)&&r.method===m).ultimate)]);
check.getRange('C34:I73').values=expectedRows;
for(let i=0;i<20;i++){
 const r=7+i;val(check,r,3,2006+i);
 for(let j=0;j<5;j++)fx(check,r,4+j,`=IF(AND(ISNUMBER('Summary'!${col(6+j)}${r}),ISNUMBER(INDEX(${col(5+j)}$34:${col(5+j)}$73,${i+1}+IF('Assumptions'!$E$4="Motor",0,20)))), 'Summary'!${col(6+j)}${r}-INDEX(${col(5+j)}$34:${col(5+j)}$73,${i+1}+IF('Assumptions'!$E$4="Motor",0,20)),"n.a.")`);
 fx(check,r,9,`=IF(ISNUMBER('Summary'!K${r}),'Summary'!L${r}-'Summary'!M${r}-'Summary'!N${r},"n.a.")`);
}
check.getRange('D7:I26').setNumberFormat('0.00');
check.getRange('D7:I26').conditionalFormats.addCustom('AND(ISNUMBER(D7),ABS(D7)>0.01)',{fill:'#fce4df',font:{color:'#9c3023'}});
note(check,29,'Reference differences compare to the original Python base run, not to a freshly calculated Python scenario.');
note(check,31,'After changing assumptions, reference differences are expected. These checks never feed the calculations.');

const sources=sheets.Sources;
const texts=[
 ['How to use','Choose Motor or Liability in Assumptions. Inspect factors, change assumptions, select methods and follow the result links.'],
 ['Workbook scope','Fixed annual example, 2006–2025 at 31 December 2025. Both portfolios use EUR after deductible.'],
 ['Source rows',`${data.rows.length.toLocaleString('en-US')} annual snapshots from the complete synthetic demo. Source ranges are fixed; do not append/re-sort rows without rebuilding references.`],
 ['Recalculation','The formulas are ordinary Excel formulas. No macros, external links or Python installation are needed to recalculate.'],
 ['Development','Volume uses sums over matching observed pairs. Simple uses their mean ratio. Exclusions apply before the newest eligible pair window.'],
 ['Tail','A factor of 1.0000 assumes no subsequent development. Tail changes and exclusions need documented judgement.'],
 ['Frequency × severity','Prior calendar years only. Amount and count CL estimate historical ultimate severity. Weighted and equal-year averages are available.'],
 ['Claims population','One stable claim ID, including zero-payment claims. Reopening does not create a new reported claim.'],
 ['Bornhuetter–Ferguson','Observed paid/incurred + expected ultimate × (1 − 1/CDF). Each basis uses its own CDF.'],
 ['Limitations','No uncertainty intervals, discounting, contract layers, formal approvals or regulatory certification. Synthetic experience is not market calibration.'],
 ['Source: methodology','Jacqueline Friedland, CAS, Estimating Unpaid Claims Using Basic Techniques, 2009, chapters 5–7, 9 and 11.'],
 ['Methodology URL','https://www.casact.org/sites/default/files/database/studynotes_friedland_estimating.pdf'],
 ['Source: independent code','Chainladder Python 0.8.26 (MPL-2.0); reference tests use the bundled RAA triangle.'],
 ['Chainladder URL','https://chainladder-python.readthedocs.io/stable/user_guide/methods.html'],
 ['Data source','Original fictitious claim simulator, seed 20260914. No client data. See docs/data_dictionary.md and docs/research.md.'],
 ['Simulation reference','https://www.casact.org/publications-research/research/loss-simulation-model-and-documentation'],
 ['Audit meaning','Stored references identify a run. They do not certify source correctness or provide a signed audit trail.'],
 ['Unavailable results','The first origin has no prior-year severity calibration. Enter an independent BF prior if that method is required.'],
 ['Deductible','Recorded metadata only. Neither this workbook nor the library subtracts it from supplied amounts.'],
];
header(sources,6,['Topic','Explanation']);sources.getRange('C7:D25').values=texts;
sources.getRange('C7:C25').format.columnWidth=27;sources.getRange('D7:D25').format.columnWidth=110;
sources.getRange('D7:D25').format.wrapText=true;sources.getRange('C7:D25').format.rowHeight=42;

// Compare all five methods for both portfolios and changed assumptions before exporting.
const checks=[];
function compare(p,scenario){
 const actual=sum.getRange('F7:J26').values;
 for(let i=0;i<20;i++)for(let j=0;j<5;j++){
  const expected=data.expected[p][scenario].find(r=>r.origin===String(2006+i)&&r.method===checkMethods[j]).ultimate;
  const got=actual[i][j];
  if(expected===null){if(got!=='n.a.')throw Error(`${p}/${scenario}/${i}/${j}: expected n.a., got ${got}`)}
  else if(typeof got!=='number'||Math.abs(expected-got)>0.01)throw Error(`${p}/${scenario}/${i}/${j}: ${got} != ${expected}`);
 }
 checks.push({portfolio:p,scenario,passed:true});
}
for(const p of ['Motor','Liability']){
 val(a,4,5,p);wb.recalculate();compare(p,'base');
 val(a,8,5,0.03);wb.recalculate();compare(p,'trend');val(a,8,5,0);
 val(a,7,5,'simple');wb.recalculate();compare(p,'simple');val(a,7,5,'weighted');
 val(a,15,4,'simple');val(a,15,5,3);val(a,15,6,1.02);wb.recalculate();compare(p,'factors');
 val(a,15,4,'volume');val(a,15,5,0);val(a,15,6,1);
 val(a,41,4,0);wb.recalculate();compare(p,'zero_prior');a.getRange('D41').clear({applyTo:'contents'});
}
val(a,4,5,'Motor');wb.recalculate();
await fs.writeFile(path.join(root,'artifacts/workbook_checks.json'),JSON.stringify(checks,null,2));
console.log(JSON.stringify(checks));
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!',options:{useRegex:true,maxResults:20},summary:'Formula errors'});
console.log(errors.ndjson);
await fs.mkdir(path.join(root,'artifacts/previews'),{recursive:true});
for(const name of names){
 const range=name==='Data'?'A1:N12':name==='Sources'?'C2:D25':name==='Assumptions'?'C2:M28':name==='Summary'?'C2:N37':name==='Checks'?'C2:I31':name==='BF'?'C2:L30':name==='Severity'?'C2:I27':'C2:L26';
 const img=await wb.render({sheetName:name,range,scale:1,format:'png'});
 await fs.writeFile(path.join(root,`artifacts/previews/${name}.png`),new Uint8Array(await img.arrayBuffer()));
}
const output=await SpreadsheetFile.exportXlsx(wb);
await output.save(path.join(root,'examples/reserving_worked_example.xlsx'));
console.log('Exported worked example.');
