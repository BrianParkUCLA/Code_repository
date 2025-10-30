# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 14:52:22 2025

Note: This script is for demonstration purposes only. It should not be construed as financial advice

@author: RBAY
"""

#!/usr/bin/env python
from __future__ import print_function

from datetime import datetime
from collections import OrderedDict
import random
import os
import pandas as pd

import axioma
from axioma.assetset import AssetSet, ActionEntry
from axioma.account import Account
from axioma.workspace import DerbyProvider, Workspace
from axioma.workspace_element import ElementType
from axioma.costmodel import CostModel, CostStructure
from axioma.group import Group, Benchmark, Unit
from axioma.contentbuilder_group import ContentBuilderBenchmark, ContentBuilderGroup
from axioma.riskmodel import RiskModel
from axioma.strategy import Strategy, Objective, Target, Scope
from axioma.rebalancing import Rebalancing, RebalancingStatus
from axioma.workspace_element import ElementType
from axioma.metagroup import Metagroup, DynamicMetagroup
from axioma.analytics import Analytics
import axioma.workspace_io as handler

os.chdir(r"C:\Users\RBAY\OneDrive - SimCorp\AXMovedFiles\Desktop\clients\Prospects\Altisma\Time Series Example")

# # cleanup
# for workspace in axioma.workspace.get_available_workspace_names():
#     axioma.workspace.get(workspace).destroy()

axioma.ENDPOINT = 'http://US05sv0040:8088/axioma-websrv'

dates = ["2024-10-01",
         "2024-10-02",
         "2024-10-03",
         "2024-10-04",
         "2024-10-07"]

model = "US51AxiomaSH"

# iterate through dates in dates list
for i in range(len(dates)-1):
    ############################## CREATE WORKSPACE
    date = datetime.strptime(dates[i], '%Y-%m-%d').date()
    next_period_date = datetime.strptime(dates[i+1], '%Y-%m-%d').date()
    axioma_data_dir = r'P:/current/riskmodels/2.1/Derby/${yyyy}/${mm}/'
    db_provider = DerbyProvider(axioma_data_dir,
                                risk_models=model,
                                include_composites=True,
                                next_period_date=next_period_date)
    
    ws = Workspace(f"AltismaWorkspace_{dates[i]}", date, data_provider=db_provider)
    
    ############################## LOAD DATA
    # load alpha capture portfolio (J)
    ac_df = pd.read_csv(f"AlphaCapture_{dates[i]}.csv", index_col="Stock_Ticker")
    Account(workspace = ws, 
            identity = "Alpha Capture (J)", 
            holdings=ac_df.to_dict()["Shares_Held"], 
            asset_map="Ticker Map")

    # this example assumes that you are using the rolled holdings from the prior period as your initial portfolio INSTEAD of taking the alpha cature as the starting in each period
    if i == 0: # in later periods, instantiate the account from the rolled holdings
        ac_account = Account(workspace = ws, identity = "Backtest Account", holdings=ac_df.to_dict()["Shares_Held"], asset_map="Ticker Map")
        ac_account.set_reference_size(reference_size=ac_account.get_long_value(price_group="Price")+ac_account.get_long_cash_value(price_group="Price"))
    else:
        handler.load_roll_forward_account(workspace=ws, data=rolled_holdings)
        ac_account = ws.get_account(rolled_holdings['identity'])
        
    
    # load ARKK, QQQ, and IWV ETFs from Axioma data set
    handler.load_assets_from_data_provider(workspace=ws, asset_names=["ARKK", "QQQ", "IWV"], asset_map="Ticker Map")
    
    # create IWV Benchmark
    beta_comp = ContentBuilderBenchmark(workspace=ws, 
                                        identity = "Beta Completion - IWV (K)", 
                                        expression = "'Composition of 7PCRDRYL0'*1")
    # create ARKK - QQQ Benchmark
    alpha_engine = ContentBuilderBenchmark(workspace=ws, 
                                           identity = "Alpha Engine - ARKK-QQQ (I)", 
                                           expression = "'Composition of M6FY3Y378'-'Composition of 3HLJW34K7'")
    # create K-I Benchmark
    kmi = ContentBuilderBenchmark(workspace=ws, 
                                  identity = "K-I", 
                                  expression="'Composition of 7PCRDRYL0'-'Composition of M6FY3Y378'+'Composition of 3HLJW34K7'")
    # create unscaled initial portfolio (alpha capture) benchmark
    alpha_capture = ContentBuilderGroup(workspace=ws, 
                                        identity = "Alpha Capture (J) - Unscaled Benchmark", 
                                        expression = "portfolioAsCurrency( 'Alpha Capture (J)', 'Price' )")
    
    # create linear t-cost model
    tcm = CostModel(workspace=ws, identity="TCost", unit=Unit.Currency)
    cost_struct = CostStructure(cost_model=tcm, identity = "Linear Charge")
    cost_struct.include_asset_set("MASTER")
    cost_struct.add_buy_slope(0, 0.02)
    cost_struct.add_sell_slope(0, 0.02)
    
    ############################## DEFINE STRATEGY
    strategy = Strategy(workspace = ws, 
                        identity = "Strategy", 
                        allow_shorting=True, 
                        allow_crossover=False, 
                        enable_constraint_hierarchy=True)
    strategy.set_local_universe(local_universe="ACCOUNT")
    ############################## DEFINE OBJECTIVE TERMS
    ar_term = axioma.strategy.create_risk_term(strategy = strategy, 
                                               identity = "activeRisk", 
                                               benchmark=alpha_capture, 
                                               risk_model=model,
                                               asset_set="MASTER")
    tc_term = axioma.strategy.create_transaction_cost_term(strategy=strategy, 
                                                           identity="transactionCost", 
                                                           base_set="MASTER")
    ############################## DEFINE OBJECTIVE FUNCTION
    terms = OrderedDict()
    terms[ar_term] = 1.0
    terms[tc_term] = 1.0
    obj_fx = Objective(strategy = strategy, 
                       identity = "Objective", 
                       terms=terms, 
                       target=Target.Minimize, 
                       active=True)
    ############################## DEFINE CONSTRAINTS
    # constraint 1
    long_leverage = axioma.strategy.create_limit_long_holding_constraint(strategy = strategy, 
                                                                         identity = "01. Limit Long Holding Limit",
                                                                         maximum=200, 
                                                                         unit=Unit.Percent,
                                                                         scope=Scope.Aggregate)
    long_leverage.add_selection(element_type=ElementType.AssetSet, element="MASTER")
    # constraint 2
    short_leverage = axioma.strategy.create_limit_short_holding_constraint(strategy=strategy, 
                                                                           identity = "02. Limit Short Holding Limit",
                                                                           maximum=200,
                                                                           unit=Unit.Percent,
                                                                           scope=Scope.Aggregate)
    short_leverage.add_selection(element_type=ElementType.AssetSet, element="MASTER")
    # # constraint 3
    # turnover = axioma.strategy.create_limit_turnover_constraint(strategy=strategy,
    #                                                             identity = "03. Two-Way Turnover",
    #                                                             maximum=200,
    #                                                             unit=Unit.Percent,
    #                                                             scope=Scope.Aggregate)
    # turnover.add_selection(element_type=ElementType.AssetSet, element="MASTER")
    # constraint 4
    mkt_exposure = axioma.strategy.create_limit_holding_constraint(strategy=strategy, 
                                                                   identity = "04. Match Market Factor Exposure of K-I", 
                                                                   minimum=-1, 
                                                                   maximum=1, 
                                                                   benchmark=kmi,
                                                                   unit=Unit.Percent,
                                                                   scope=Scope.Member)
    mkt_exposure.add_selection(element_type=ElementType.Metagroup, element=f"{model}.Market")
    # # constraint 5
    # ind_exposure = axioma.strategy.create_limit_holding_constraint(strategy=strategy,
    #                                                                identity="05. Match Industry Exposures of K-I", 
    #                                                                minimum=-2, 
    #                                                                maximum=2,
    #                                                                benchmark=kmi,
    #                                                                unit=Unit.Percent,
    #                                                                scope=Scope.Member)
    # ind_exposure.add_selection(element_type=ElementType.Metagroup, element=f"{model}.Industry")
    # constraint 6
    style_exp = axioma.strategy.create_limit_holding_constraint(strategy=strategy,
                                                                identity="06. Match Style Factor Exposures of K-I",
                                                                minimum=-0.01,
                                                                maximum=0.01,
                                                                benchmark=kmi,
                                                                unit=Unit.Number,
                                                                scope=Scope.Member)
    style_exp.add_selection(element_type=ElementType.Metagroup, element=f"{model}.Style")
    # constraint 7
    pos_size = axioma.strategy.create_limit_holding_constraint(strategy=strategy,
                                                               identity="07. Max Position Size", 
                                                               minimum=-3,
                                                               maximum=3,
                                                               unit=Unit.Percent,
                                                               scope=Scope.Asset)
    pos_size.add_selection(element_type=ElementType.AssetSet, element="MASTER")
    ############################## SET CONSTRAINT HIERARCHY CONSTRAINTS
    #strategy.set_constraint_hierarchy({"06. Match Style Factor Exposures of K-I" : 1, "05. Match Industry Exposures of K-I" : 2})
    strategy.set_constraint_hierarchy({"06. Match Style Factor Exposures of K-I" : 1})
    
    ############################## CREATE REBALANCING
    rebal = Rebalancing(workspace = ws, 
                        identity="Alpha Capture (J) Rebalancing",
                        account=ac_account, 
                        strategy=strategy)
    rebal.set_rebalancing_defaults(cost_model=tcm,risk_model=model)
    
    ############################## SOLVE REBALANCING
    sol = rebal.solve()
    print(sol.get_status())
    if sol.get_status()==RebalancingStatus.SolutionFound or sol.get_status()==RebalancingStatus.RelaxedSolutionFound:
        fh = sol.get_final_holdings(asset_map = "Ticker Map")
    
    ############################## CALCULATE ANALYTICS - THESE ARE EXAMPLES OF SOME AVAILABLE ANALYTICS
    # create Analytics object. This will be used to calculate analytics
    analyzer = Analytics(workspace = ws, price_group="Price", asset_map="Ticker Map")
    # compute active holdings of final holdings to K-I
    ah = analyzer.compute_active_holdings(holdings=fh, benchmark=kmi, reference_value=rebal.get_reference_size())
    # calculate active exposures with respect to K-I -> you divide df by reference size to convert from currency values to decimal
    ah_exposures = pd.DataFrame.from_dict({"Exposure":analyzer.compute_factor_exposures(risk_model=model,holdings=ah)})/rebal.get_reference_size()
    # compute tracking error with respect to alpha capture (J) portfolio. Compute active holdings and then calculate total risk
    delta_holdings = analyzer.compute_active_holdings(holdings=fh, benchmark=alpha_capture, reference_value=alpha_capture.get_composition_sum())
    delta_risk = analyzer.compute_total_risk(risk_model=model,holdings=delta_holdings)/rebal.get_reference_size()*100
    
    ############################## ROLL PORTFOLIO
    rolled_holdings = sol.roll_forward()
    
    # write workspace to .wsp file and release license token
    ws.write(os.getcwd(),file_name=f"workspace_on_{dates[i]}.wsp",save_reference=False)
    ws.destroy()
