export function calculate(s,data,progress=()=>{}){
 const start=performance.now(), scenarios=[], curves=[];
 function scenario(growth){const cash=new Float64Array(s.years);for(let p=0;p<data.length;p+=2){let income=data[p],cost=data[p+1];for(let y=0;y<s.years;y++){cash[y]+=income-cost;income*=1+growth/100;cost*=1+s.inflation/100}}let npv=0,factor=1;for(let y=0;y<s.years;y++){factor*=1+s.discount/100;npv+=cash[y]/factor}return {cash:Array.from(cash),npv}}
 for(let k=0;k<s.scenarios;k++){const growth=s.growth+(s.scenarios===1?0:-s.spread+2*s.spread*k/(s.scenarios-1));const r=scenario(growth);scenarios.push({growth,npv:r.npv});if(k===0||k===s.scenarios-1)curves.push(r);if(k%10===0)progress(Math.round((k+1)/s.scenarios*100))}
 const base=scenario(s.growth);return {scenarios,low:curves[0].cash,high:curves.at(-1).cash,base:base.cash,lowNpv:curves[0].npv,highNpv:curves.at(-1).npv,baseNpv:base.npv,ms:performance.now()-start};
}
if(typeof self!=='undefined')self.onmessage=({data:{s,data}})=>self.postMessage(calculate(s,data,progress=>self.postMessage({progress})));
