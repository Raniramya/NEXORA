import numpy as np
import pandas as pd

TRUE_GRAPH=[["season","traffic"],["marketing_spend","traffic"],["discount","conversion"],["price","conversion"],["competitor_price","price"],["inventory","sales"],["traffic","sales"],["conversion","sales"],["sales","revenue"]]
PARAMETERS={"marketing_to_traffic":4.0,"discount_to_conversion":.12,"price_to_conversion":-.08,"sales_to_revenue":10.0}

def generate(seed=42,n=500):
 r=np.random.default_rng(seed); season=r.integers(0,4,n); marketing=r.normal(50,10,n); competitor=r.normal(100,8,n); price=110+.5*competitor+r.normal(0,3,n); discount=r.uniform(0,.3,n); inventory=r.normal(1000,120,n); traffic=200+30*season+4*marketing+r.normal(0,20,n); conversion=.1+.12*discount-.08*(price-100)/100+r.normal(0,.02,n); sales=np.minimum(inventory,traffic*np.clip(conversion,.01,.6)); revenue=sales*price
 return pd.DataFrame({"season":season,"marketing_spend":marketing,"discount":discount,"price":price,"inventory":inventory,"competitor_price":competitor,"traffic":traffic,"conversion":conversion,"sales":sales,"revenue":revenue})

def cases(seed=42,count=180):
 kinds=["descriptive","predictive","causal","counterfactual","prescriptive","insufficient_evidence","confounding","ood_adversarial"]
 return [{"id":f"bb-{i:03d}","type":kinds[i%len(kinds)],"question":f"Benchmark {kinds[i%len(kinds)]} question {i}","allowed_evidence":["summary"],"ground_truth":{"discount_effect":PARAMETERS["discount_to_conversion"]},"evaluation_method":"type_specific"} for i in range(count)]
