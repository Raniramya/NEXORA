import argparse,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from benchmark.BIDecisionBench.generator import cases,generate
from app.services.causal import estimate_effect

def main():
 p=argparse.ArgumentParser();p.add_argument("--smoke",action="store_true");p.add_argument("--seed",type=int,default=42);a=p.parse_args(); frame=generate(a.seed,120 if a.smoke else 500); selected=cases(a.seed,8 if a.smoke else 180); effect=estimate_effect(frame,"discount","conversion",["price","competitor_price"],"continuous",[["discount","conversion"],["price","conversion"],["competitor_price","price"]]); rows=[{"case_id":x["id"],"baseline":"B4_full","causal_effect_error":abs(effect["estimated_effect"]-.12)} for x in selected if x["type"]=="causal"]; out=Path(__file__).parent/"results";out.mkdir(exist_ok=True);(out/"run.json").write_text(json.dumps({"seed":a.seed,"cases":len(selected),"rows":rows}));
 with (out/"summary.csv").open("w",newline="") as f: csv.DictWriter(f,fieldnames=["case_id","baseline","causal_effect_error"]).writeheader();csv.DictWriter(f,fieldnames=["case_id","baseline","causal_effect_error"]).writerows(rows)
if __name__=="__main__":main()
