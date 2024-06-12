# ========================================================================================= #
#               European Commission Debt Sustainability Analysis - Base Class               #
# ========================================================================================= #
#
# The DsaModel class serves as the base framework for simulating baseline and detemrinistic 
# scenario debt paths following the methodology of the European Commission's Debt Sustainability 
# Monitor. The class encompasses three primary parts:
#
# 1. **Data Methods:** These methods clean and combine input data. Input data can be compiled using 
#    the provided jupyter notebook "01_data_preparation.ipynb".
# 2. **Projection Methods:** These methods handle the projection of economic variables such as GDP
#    growth, primary balance, interest rates, and debt dynamics, based on different scenarios and
#    adjustment steps.
# 3. **Optimization and Auxiliary Methods:** These methods include functions to optimize the primary
#    balance to meet specific criteria, and check deterministic conditions.
#
# In addition, the StochasticDsaModel subclass, a specialized subclass building upon this base class,
# provides additional features for stochastic projection around the deterministic debt path.
#
# For comments and suggestions please contact lennard.welslau[at]gmail[dot]com
#
# Author: Lennard Welslau
# Updated: 2024-06-01
#
# ========================================================================================= #

# Import libraries and modules
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
sns.set_style('whitegrid')
sns.set_palette('colorblind')


class DsaModel:

# ========================================================================================= #
#                                   INIITIALIZE MODEL                                       #
# ========================================================================================= #
    
    def __init__(
            self,
            country,  # ISO code of country
            start_year=2023,  # start year of projection, first year is baseline value
            end_year=2070,  # end year of projection
            adjustment_period=4,  # number of years for linear spb_bca adjustment
            adjustment_start_year=2025,  # start year of linear spb_bca adjustment
            ageing_cost_period=10,  # number of years for ageing cost adjustment after adjustment period
            fiscal_multiplier=0.75, 
            growth_policy=False,
            growth_policy_effect=0,
            growth_policy_cost=0,
            growth_policy_period=1,
    ):

        # Initialize model parameters
        self.country = country # country ISO code
        self.start_year = start_year # start year of projection (T), normally this is the last year of non-forecast observations
        self.end_year = end_year # end year of projection (T+30)
        self.projection_period = self.end_year - start_year + 1 # number of years in projection
        self.adjustment_period = adjustment_period # adjustment period for structural primary balance, for COM 4 or 7 years
        adjustment_start_year = adjustment_start_year # start year of adjustment period
        self.adjustment_start = adjustment_start_year - start_year # start (T+x) of adjustment period
        self.adjustment_end = adjustment_start_year + adjustment_period - start_year - 1  # end (T+x) of adjustment period
        self.ageing_cost_period = ageing_cost_period # number of years during which ageing costs have to be accounted for by spb adjustment
        self.fiscal_multiplier = fiscal_multiplier # fiscal multiplier for fiscal adjustment
        self.growth_policy = growth_policy # True if growth policy is applied
        self.growth_policy_effect = growth_policy_effect # effect of growth policy on GDP growth
        self.growth_policy_cost = growth_policy_cost # cost of growth policy as share of GDP
        self.growth_policy_period = growth_policy_period # number of years from adjustment start during which growth policy is applied

        # Initialize model variables related to GDP, growth, inflation
        self.rg_bl = np.full(self.projection_period, np.nan, dtype=np.float64)  # baseline growth rate
        self.ng_bl = np.full(self.projection_period, np.nan, dtype=np.float64)  # baseline nominal growth rate
        self.ngdp_bl = np.full(self.projection_period, np.nan, dtype=np.float64)  # baseline nominal GDP
        self.rgdp_bl = np.full(self.projection_period, np.nan, dtype=np.float64)  # baseline real GDP
        self.output_gap_bl = np.full(self.projection_period, np.nan, dtype=np.float64)  # baseline output gap
        self.rg = np.full(self.projection_period, np.nan, dtype=np.float64)  # real growth rate adjusted for fiscal_multiplier
        self.ng = np.full(self.projection_period, np.nan, dtype=np.float64)  # nominal growth rate
        self.ngdp = np.full(self.projection_period, np.nan, dtype=np.float64)  # nominal GDP adjusted for fiscal_multiplier
        self.rgdp = np.full(self.projection_period, np.nan, dtype=np.float64)  # real GDP adjusted for fiscal_multiplier
        self.rgdp_pot = np.full(self.projection_period, np.nan, dtype=np.float64)  # potential GDP
        self.output_gap = np.full(self.projection_period, np.nan, dtype=np.float64)  # output gap
        self.rg_pot = np.full(self.projection_period, np.nan, dtype=np.float64)  # potential growth rate
        self.pi = np.full(self.projection_period, np.nan, dtype=np.float64)  # inflation rate
        self.fm_effect = np.full(self.projection_period, 0, dtype=np.float64)  # fiscal multiplier impulse

        # Extension for analysis of temporary growth policy
        self.growth_policy_cost_inflated = np.full(self.projection_period, 0, dtype=np.float64)  # cost of growth policy
        self.growth_policy_cost_ratio = np.full(self.projection_period, 0, dtype=np.float64)  # cost of growth policy as share of GDP

        # Initialize model variables related to primary balance and components
        self.ageing_cost = np.full(self.projection_period, np.nan, dtype=np.float64)  # ageing cost
        # self.property_income = np.full(self.projection_period, np.nan, dtype=np.float64)  # property income
        # self.property_income_component = np.full(self.projection_period, np.nan, dtype=np.float64)  # property income component of primary balance
        self.cyclical_component = np.full(self.projection_period, 0, dtype=np.float64)  # cyclical_component component of primary balance
        self.ageing_component = np.full(self.projection_period, 0, dtype=np.float64)  # ageing_component component of primary balance
        self.PB = np.full(self.projection_period, np.nan, dtype=np.float64)  # primary balance
        self.pb = np.full(self.projection_period, np.nan, dtype=np.float64)  # primary balance over GDP
        self.SPB = np.full(self.projection_period, np.nan, dtype=np.float64)  # structural primary balance
        self.spb_bl = np.full(self.projection_period, np.nan, dtype=np.float64)  # baseline primary balance over GDP
        self.spb_bca = np.full(self.projection_period, np.nan, dtype=np.float64)  # structural primary balance over GDP before cost of ageing
        self.spb = np.full(self.projection_period, np.nan, dtype=np.float64)  # structural primary balance over GDP
        self.spb_bca_adjustment = np.full(self.projection_period, np.nan, dtype=np.float64)  # change in structural primary balance
        self.GFN = np.full(self.projection_period, np.nan, dtype=np.float64)  # gross financing needs
        self.SF = np.full(self.projection_period, 0, dtype=np.float64)  # stock-flow adjustment
        self.sf = np.full(self.projection_period, 0, dtype=np.float64)  # stock-flow adjustment over GDP
        self.ob = np.full(self.projection_period, np.nan, dtype=np.float64)  # fiscal balance
        self.sb = np.full(self.projection_period, np.nan, dtype=np.float64)  # structural balance

        # Initialize model variables related to debt and interest variables
        self.D = np.full(self.projection_period, 0, dtype=np.float64)  # total debt
        self.d = np.full(self.projection_period, np.nan, dtype=np.float64)  # debt to GDP ratio
        self.D_lt = np.full(self.projection_period, 0, dtype=np.float64)  # total long-term debt
        self.D_new_lt = np.full(self.projection_period, 0, dtype=np.float64)  # new long-term debt
        self.D_lt_esm = np.full(self.projection_period, 0, dtype=np.float64)  # inst debt
        self.D_st = np.full(self.projection_period, 0, dtype=np.float64)  # total short-term debt
        self.D_share_lt_maturing = np.full(self.projection_period, np.nan, dtype=np.float64)  # share of long-term debt maturing in the current year
        self.repayment_st = np.full(self.projection_period, np.nan, dtype=np.float64)  # repayment of short-term debt
        self.repayment_lt = np.full(self.projection_period, np.nan, dtype=np.float64)  # repayment of long-term debt
        self.repayment_lt_esm = np.full(self.projection_period, 0, dtype=np.float64)  # repayment of inst debt
        self.repayment = np.full(self.projection_period, np.nan, dtype=np.float64)  # repayment of total debt
        self.interest_st = np.full(self.projection_period, np.nan, dtype=np.float64)  # interest payment on short-term debt
        self.interest_lt = np.full(self.projection_period, np.nan, dtype=np.float64)  # interest payment on long-term debt
        self.interest = np.full(self.projection_period, np.nan, dtype=np.float64)  # interest payment on total debt
        self.interest_ratio = np.full(self.projection_period, np.nan, dtype=np.float64)  # interest payment over GDP
        self.i_st = np.full(self.projection_period, np.nan, dtype=np.float64)  # market interest rate on short-term debt
        self.i_lt = np.full(self.projection_period, np.nan, dtype=np.float64)  # market interest rate on long-term debt
        self.exr_eur = np.full(self.projection_period, np.nan, dtype=np.float64)  # euro exchange rate
        self.exr_usd = np.full(self.projection_period, np.nan, dtype=np.float64)  # usd exchange rate
        self.iir_bl = np.full(self.projection_period, np.nan, dtype=np.float64)  # baseline implicit interest rate
        self.alpha = np.full(self.projection_period, np.nan, dtype=np.float64)  # share of short-term debt in total debt
        self.beta = np.full(self.projection_period, np.nan, dtype=np.float64)  # share of new long-term debt in total long-term debt
        self.iir = np.full(self.projection_period, np.nan, dtype=np.float64)  # impoict interest rate
        self.iir_lt = np.full(self.projection_period, np.nan, dtype=np.float64)  # implicit long-term interest rate

        # Auxiliary variables for stochastic simulations
        self.exr = np.full(self.projection_period, np.nan, dtype=np.float64)  # exchange rate

        # Clean data
        self._clean_data()

# ========================================================================================= #
#                               DATA METHODS (INTERNAL)                                     #
# ========================================================================================= #

    def _clean_data(self):
        """
        Import data from CSV deterministic input data file.
        """
        self.df_deterministic_data = pd.read_csv('../data/InputData/deterministic_data.csv')
        self.df_deterministic_data = self.df_deterministic_data.loc[self.df_deterministic_data['COUNTRY'] == self.country].set_index('YEAR').iloc[:,1:]

        self._clean_rgdp_pot()
        self._clean_rgdp()
        if self.growth_policy:
            self._apply_growth_policy_effect()
        self._calculate_output_gap()
        self._clean_inflation()
        self._clean_ngdp()
        self._clean_debt()
        self._clean_esm_repayment()
        self._clean_debt_redemption()
        self._clean_pb()
        self._clean_implicit_interest_rate()
        self._clean_forward_rates()
        self._clean_stock_flow()
        self._clean_exchange_rate()
        self._clean_ageing_cost()

    def _clean_rgdp_pot(self):
        """
        Clean baseline real potential growth.
        """
        for t, y in enumerate(range(self.start_year, self.end_year + 1)):
            
            # potential growth is based on OGWG up to T+5, long-run estimates from 2033, interpoalted in between
            self.rg_pot[t] = self.df_deterministic_data.loc[y, 'POTENTIAL_GDP_GROWTH']
            
            # potential GDP up to T+5 are from OGWG, after that projected based on growth rate
            if t <= 5:
                self.rgdp_pot[t] = self.df_deterministic_data.loc[y, 'POTENTIAL_GDP']
            else:
                self.rgdp_pot[t] = self.rgdp_pot[t - 1] * (1 + self.rg_pot[t] / 100)    

    def _clean_rgdp(self):
        """
        Clean baseline real growth. Baseline refers to forecast values without fiscal multiplier effect.
        """
        for t, y in enumerate(range(self.start_year, self.end_year + 1)):
            
            # potential GDP up to T+5 are from OGWG, after that projected based on growth rate
            if t <= 5:
                self.rgdp_bl[t] = self.df_deterministic_data.loc[y, 'REAL_GDP']
                self.rg_bl[t] = self.df_deterministic_data.loc[y, 'REAL_GDP_GROWTH']

            else:
                self.rgdp_bl[t] = self.rgdp_pot[t]
                self.rg_bl[t] = self.rg_pot[t]

        # Set initial values to baseline
        self.rg = np.copy(self.rg_bl)
        self.rgdp = np.copy(self.rgdp_bl)

    def _apply_growth_policy_effect(self):
        """
        Apply growth enhancing policy to potential and real GDP.
        """
        for t in range(self.adjustment_start, self.projection_period):

            # Calcualte increase of real potential gdp during policy period
            if t in range(self.adjustment_start, self.adjustment_start + self.growth_policy_period):
                rgdp_pot_annual_effect = (self.rgdp_pot[self.adjustment_start + self.growth_policy_period - 1]
                                          * (self.growth_policy_effect / 100)
                                          * (t - self.adjustment_start + 1) / self.growth_policy_period)

                # Apply increase to rgdp
                self.rgdp_pot[t] += rgdp_pot_annual_effect
                self.rgdp_bl[t] += rgdp_pot_annual_effect
                self.rgdp[t] += rgdp_pot_annual_effect

                # Recalculate implied growth rates
                self.rg_pot[t] = (self.rgdp_pot[t] - self.rgdp_pot[t - 1]) / self.rgdp_pot[t - 1] * 100
                self.rg_bl[t] = (self.rgdp_bl[t] - self.rgdp_bl[t - 1]) / self.rgdp_bl[t - 1] * 100
                self.rg[t] = (self.rgdp[t] - self.rgdp[t - 1]) / self.rgdp[t - 1] * 100

            # Use default growth rates to project GDP after
            else:
                self.rgdp_pot[t] = self.rgdp_pot[t - 1] * (1 + self.rg_pot[t] / 100)
                self.rgdp_bl[t] = self.rgdp_bl[t - 1] * (1 + self.rg_bl[t] / 100)
                self.rgdp[t] = self.rgdp_bl[t - 1] * (1 + self.rg[t] / 100)

    def _calculate_output_gap(self):
        """
        Calculate the Output gap.
        """ 
        for t, y in enumerate(range(self.start_year, self.end_year + 1)):
            self.output_gap_bl[t] = (self.rgdp_bl[t] / self.rgdp_pot[t] - 1) * 100

        # Set initial values to baseline
        self.output_gap = np.copy(self.output_gap_bl)

    def _clean_inflation(self):
        """
        Clean inflation rate data.
        """
        # Up to T+3 from Ameco GDP deflator
        for t, y in enumerate(range(self.start_year, self.start_year + 3)):
            self.pi[t] = self.df_deterministic_data.loc[y, 'GDP_DEFLATOR_PCH']

        # Set T+10 value based on inflation swaps, T+30 is 2 percent
        self.pi[10] = self.df_deterministic_data.loc[0, 'FWD_INFL_5Y5Y']
        self.pi[30] = 2

        # Poland and Romania T+10 target is increased by half of the difference with Euro Area in T+2
        # T+30 target is set to 2.5 for Poland and Romania, 3 for Hungary
        if self.country in ['POL', 'ROU']:
            self.pi[10] += (self.pi[2] - self.df_deterministic_data.loc[self.start_year+2, 'EA_GDP_DEFLATOR_PCH']) / 2
            self.pi[30] = 2.5
        elif self.country in ['HUN']:
            self.pi[30] += 1

        # Interpolate missing values
        x = np.arange(len(self.pi))
        mask_pi = np.isnan(self.pi)
        self.pi[mask_pi] = np.interp(x[mask_pi], x[~mask_pi], self.pi[~mask_pi])
        
    def _clean_ngdp(self):
        """
        Clean baseline nominal growth.
        """
        for t, y in enumerate(range(self.start_year, self.end_year + 1)):
            
            # Up to T+3 from Ameco Nominal GDP, after that projected based on growth rate
            if t <= 2:
                self.ngdp_bl[t] = self.df_deterministic_data.loc[y, 'NOMINAL_GDP']
                self.ng_bl[t] = self.df_deterministic_data.loc[y, 'NOMINAL_GDP_GROWTH']
            else:
                self.ng_bl[t] = (1 + self.rg_bl[t] / 100) * (1 + self.pi[t] / 100) * 100 - 100
                self.ngdp_bl[t] = self.ngdp_bl[t - 1] * (1 + self.ng_bl[t] / 100)

        # Set initial values to baseline
        self.ng = np.copy(self.ng_bl)
        self.ngdp = np.copy(self.ngdp_bl)

    def _clean_debt(self):
        """
        Clean debt data and parameters.
        """
        # Get baseline debt from Ameco
        for t, y in enumerate(range(self.start_year, self.start_year + 3)):
            self.d[t] = self.df_deterministic_data.loc[y, 'DEBT_RATIO']
            self.D[t] = self.df_deterministic_data.loc[y, 'DEBT_TOTAL']
        
        # Set maturity shares and average maturity
        self.D_share_st = self.df_deterministic_data.loc[0, 'DEBT_ST_SHARE']
        self.D_share_lt = 1 - self.D_share_st
        self.D_share_lt_maturing_T = self.df_deterministic_data.loc[0, 'DEBT_LT_MATURING_SHARE']
        self.D_share_lt_mat_avg = self.df_deterministic_data.loc[0, 'DEBT_LT_MATURING_AVG_SHARE']
        self.avg_res_mat = min(round((1 / self.D_share_lt_mat_avg)), 30)

        # Set share of domestic, euro and usd debt, ensure no double counting for non-euro countries
        self.D_share_domestic = np.round(self.df_deterministic_data.loc[0, 'DEBT_DOMESTIC_SHARE'], 4)
        if self.country in ['BGR', 'CZE', 'DNK', 'HUN', 'POL', 'ROU', 'SWE', 'GBR', 'USA']:
            self.D_share_eur = np.round(self.df_deterministic_data.loc[0, 'DEBT_EUR_SHARE'], 4)
        else:
            self.D_share_eur = 0
        if self.country != 'USA':
            self.D_share_usd = np.round(1 - self.D_share_domestic - self.D_share_eur, 4)
        else:
            self.D_share_usd = 0

        # Set initial values for long and short-term debt
        self.D_st[0] = self.D_share_st * self.D[0]
        self.D_lt[0] = self.D_share_lt * self.D[0] 

    def _clean_esm_repayment(self):
        """
        Clean institutional debt data.
        """
        # Set to zero if missing
        self.df_deterministic_data['ESM_REPAYMENT'].fillna(0, inplace=True)

        # Calculate initial value of institutional debt 
        self.D_lt_esm[0] = self.df_deterministic_data['ESM_REPAYMENT'].sum()
        
        # Import ESM institutional debt repayments
        for t, y in enumerate(range(self.start_year + 1, self.end_year + 1)):
            self.repayment_lt_esm[t] = self.df_deterministic_data.loc[y, 'ESM_REPAYMENT']
            self.D_lt_esm[t] = self.D_lt_esm[t - 1] - self.repayment_lt_esm[t] if t > 0 else self.D_lt_esm[0]

    def _clean_debt_redemption(self):
        """
        Clean debt redemption data for institutional debt.
        """
        # Set T and T + 10 value of maturing lt debt share
        self.D_share_lt_maturing[0] = self.D_share_lt_maturing_T
        self.D_share_lt_maturing[10:] = self.D_share_lt_mat_avg

        # Interpolate missing values
        x = np.arange(len(self.D_share_lt_maturing))
        mask = np.isnan(self.D_share_lt_maturing)
        self.D_share_lt_maturing[mask] = np.interp(x[mask], x[~mask], self.D_share_lt_maturing[~mask])
    
    def _clean_pb(self):
        """
        Clean structural primary balance.
        """
        # Get baseline spb from Ameco
        for t, y in enumerate(range(self.start_year, self.end_year + 1)):
            if t <= 2:
                self.spb_bl[t] = self.df_deterministic_data.loc[y, 'STRUCTURAL_PRIMARY_BALANCE']
                self.pb[t] = self.df_deterministic_data.loc[y, 'PRIMARY_BALANCE']
                self.ob[t] = self.df_deterministic_data.loc[y, 'FISCAL_BALANCE']
            else:
                self.spb_bl[t] = self.spb_bl[t - 1]
                self.pb[t] = self.pb[t - 1]
        
        # Set initial values to baseline
        self.spb_bca = np.copy(self.spb_bl)
        self.spb = np.copy(self.spb_bl)

        # Get budget balance semi-elasticity
        self.budget_balance_elasticity = self.df_deterministic_data.loc[0, 'BUDGET_BALANCE_ELASTICITY']
    
    def _clean_implicit_interest_rate(self):
        """
        Clean implicit interest rate.
        """
        # Get implicit interest rate from Ameco
        for t, y in enumerate(range(self.start_year, self.start_year + 3)):
            self.iir[t] = self.df_deterministic_data.loc[y, 'IMPLICIT_INTEREST_RATE']

        # Initial lt baseline
        self.iir_lt[0] = self.iir[0] * (1 - self.D_share_st)
    
    def _clean_forward_rates(self):
        """
        Clean forward Bloomberg forward and benchmark rates.
        """
        # Get benchmark rates for first years
        for t, y in enumerate(range(self.start_year, self.start_year + 2)):
            self.i_st[t] = self.df_deterministic_data.loc[y, 'INTEREST_RATE_ST']
            self.i_lt[t] = self.df_deterministic_data.loc[y, 'INTEREST_RATE_LT']

        # Load 10 year forward rates
        self.fwd_rate_st = self.df_deterministic_data.loc[0, 'FWD_RATE_3M10Y']
        self.fwd_rate_lt = self.df_deterministic_data.loc[0, 'FWD_RATE_10Y10Y']

    def _clean_stock_flow(self):
        """
        Clean stock flow adjustment.
        """
        # Get stock-flow adjustment from Ameco
        for t, y in enumerate(range(self.start_year, self.start_year + 3)):
            self.SF[t] = self.df_deterministic_data.loc[y, 'STOCK_FLOW']

        # For Luxembourg, Finland, get Pension balance ratio for projection
        if self.country in ['LUX', 'FIN']:
            self.pension_balance_ratio = np.full(self.projection_period, 0, dtype=np.float64)
            for t, y in enumerate(range(self.start_year, self.end_year + 1)):
                self.pension_balance_ratio[t] = self.df_deterministic_data.loc[y, 'PENSION_BALANCE']

    def _clean_exchange_rate(self):
        """
        Clean exchange rate data for non-euro countries.
        """
        # Get exchange rate data from Ameco
        for t, y in enumerate(range(self.start_year, self.end_year + 1)):

            if t <= 2:
                self.exr_eur[t] = self.df_deterministic_data.loc[y, 'EXR_EUR']
                self.exr_usd[t] = self.df_deterministic_data.loc[y, 'EXR_USD']
            else:
                self.exr_usd[t] = self.exr_usd[t - 1]
                self.exr_eur[t] = self.exr_eur[t - 1]

    def _clean_ageing_cost(self):
        """
        Clean ageing cost data.
        """
        # Import ageing costs from Ageing Report data
        for t, y in enumerate(range(self.start_year, self.end_year + 1)):
            self.ageing_cost[t] = self.df_deterministic_data.loc[y, 'AGEING_COST']
    
    # def _clean_property_income(self):
    #     """
    #     Clean property income data.
    #     """
    #     for t, y in enumerate(range(self.start_year, self.end_year + 1)):
    #         self.property_income[t] = self.df_property_income.loc[y]

# ========================================================================================= #
#                                   PROJECTION METHODS                                      #
# ========================================================================================= #

    def project(self,
                spb_target=None,
                adjustment_steps=None,  # list of annual adjustment steps during adjustment
                edp_steps=None,  # list of annual adjustment steps during EDP
                deficit_resilience_steps=None,  # list of years during adjustment where minimum step size is enforced
                post_adjustment_steps=None,  # list of years after adjustment where minimum step size is enforced
                scenario='main_adjustment',  # scenario parameter, needed for DSA criteria
                ):
        """
        Project debt dynamics
        """
        # Clear starting values from memory
        self.D_new_lt = np.full(self.projection_period, 0, dtype=np.float64)
        self._clean_implicit_interest_rate()

        # Set spb_target
        if (spb_target is None
                and adjustment_steps is None):
            self.spb_target = self.spb_bca[self.adjustment_start - 1]
        elif (spb_target is None
              and adjustment_steps is not None):
            self.spb_target = self.spb_bca[self.adjustment_start - 1] + adjustment_steps.sum()
        else:
            self.spb_target = spb_target

        # Set adjustment steps
        if (adjustment_steps is None
                and spb_target is not None):
            # If adjustment steps are predifined, adjust only non-nan values
            if hasattr(self, 'predefined_adjustment_steps'):
                self.adjustment_steps = np.copy(self.predefined_adjustment_steps)
                last_non_nan = np.where(~np.isnan(self.predefined_adjustment_steps))[0][-1]
                num_steps = self.adjustment_period - (last_non_nan + 1)
                step_size = (spb_target - self.spb_bca[self.adjustment_start+last_non_nan]) / num_steps
                self.adjustment_steps[last_non_nan+1:] = np.full(num_steps, step_size)
            else:
                self.adjustment_steps = np.full((self.adjustment_period,), (self.spb_target - self.spb_bca[self.adjustment_start - 1]) / self.adjustment_period, dtype=np.float64)
        elif (adjustment_steps is None
              and spb_target is None):
            self.adjustment_steps = np.full((self.adjustment_period,), 0, dtype=np.float64)
        else:
            self.adjustment_steps = adjustment_steps

        # Set edp steps
        if edp_steps is None:
            self.edp_steps = np.full((self.adjustment_period,), np.nan, dtype=np.float64)
        else:
            self.edp_steps = edp_steps

        # Set deficit resilience steps
        if deficit_resilience_steps is None:
            self.deficit_resilience_steps = np.full((self.adjustment_period,), np.nan, dtype=np.float64)
        else:
            self.deficit_resilience_steps = deficit_resilience_steps

        # Set post adjustment steps
        if post_adjustment_steps is None:
            self.post_adjustment_steps = np.full((self.projection_period - self.adjustment_end - 1,), 0, dtype=np.float64)
        else:
            self.post_adjustment_steps = post_adjustment_steps

        # Set scenario parameter
        self.scenario = scenario

        # Project debt dynamics
        self._project_net_expenditure_path()
        self._project_market_rate()
        self._project_gdp()
        self._project_stock_flow()
        self._project_spb()
        self._project_pb()
        self._project_debt_ratio()

    def _project_net_expenditure_path(self):
        """
        Project structural primary balance, excluding ageing cost
        """
        # Adjust path for EDP and deficit resilience steps
        self._adjust_for_edp()
        self._adjust_for_deficit_resilience()
        self._apply_adjustment_steps()

        # If lower_spb scenario, adjust path
        if self.scenario == 'lower_spb':
            self._apply_lower_spb()

        # If growth policy, adjust path
        if self.growth_policy:
            self._calculate_growth_policy_cost()

    def _adjust_for_edp(self):
        """
        Adjust linear path for minimum EDP adjustment steps
        """
        # Save copy of baseline adjustment steps
        self.adjustment_steps_baseline = np.copy(self.adjustment_steps)

        # Apply EDP steps to adjustment steps
        self.adjustment_steps[~np.isnan(self.edp_steps)] = np.where(
            self.edp_steps[~np.isnan(self.edp_steps)] > self.adjustment_steps[~np.isnan(self.edp_steps)],
            self.edp_steps[~np.isnan(self.edp_steps)],
            self.adjustment_steps[~np.isnan(self.edp_steps)]
        )

        # Identify periods that are after EDP and correct them for frontloading
        if not np.isnan(self.edp_steps).all():
            last_edp_index = np.where(~np.isnan(self.edp_steps))[0][-1]
        else:
            last_edp_index = 0
        post_edp_index = np.arange(last_edp_index + 1, len(self.adjustment_steps))
        self.diff_adjustment_baseline = np.sum(self.adjustment_steps_baseline - self.adjustment_steps)
        offset_edp = self.diff_adjustment_baseline / len(post_edp_index) if len(post_edp_index) > 0 else 0
        self.adjustment_steps[post_edp_index] += offset_edp

    def _adjust_for_deficit_resilience(self):
        """
        Adjust linear path for minimum deficit resilience adjustment steps
        """
        # Save copy of edp adjusted steps
        self.adjustment_steps_baseline = np.copy(self.adjustment_steps)

        # Apply deficit resilience safeguard steps to adjustment steps
        self.adjustment_steps[~np.isnan(self.deficit_resilience_steps)] = np.where(
            self.deficit_resilience_steps[~np.isnan(self.deficit_resilience_steps)] > self.adjustment_steps[~np.isnan(self.deficit_resilience_steps)],
            self.deficit_resilience_steps[~np.isnan(self.deficit_resilience_steps)],
            self.adjustment_steps[~np.isnan(self.deficit_resilience_steps)]
        )

        # Identify periods that are after EDP and deficit resilience and correct for frontloading
        if not (np.isnan(self.edp_steps).all()
                and np.isnan(self.deficit_resilience_steps).all()):
            last_edp_deficit_resilience_index = np.where(~np.isnan(self.edp_steps) | ~np.isnan(self.deficit_resilience_steps))[0][-1]
        else:
            last_edp_deficit_resilience_index = 0
        post_edp_deficit_resilience_index = np.arange(last_edp_deficit_resilience_index + 1, len(self.adjustment_steps))
        self.diff_adjustment_baseline = np.sum(self.adjustment_steps_baseline - self.adjustment_steps)
        self.offset_deficit_resilience = self.diff_adjustment_baseline / len(post_edp_deficit_resilience_index) if len(post_edp_deficit_resilience_index) > 0 else 0
        self.adjustment_steps[post_edp_deficit_resilience_index] += self.offset_deficit_resilience

    def _apply_adjustment_steps(self):
        """
        Project spb_bca
        """
        # Apply adjustment steps based on the current period
        for t in range(self.adjustment_start, self.projection_period):
            if t in range(self.adjustment_start, self.adjustment_end + 1):
                self.spb_bca[t] = self.spb_bca[t - 1] + self.adjustment_steps[t - self.adjustment_start]
            else:
                self.spb_bca[t] = self.spb_bca[t - 1] + self.post_adjustment_steps[t - self.adjustment_end - 1]

        # Save adjustment step size
        self.spb_bca_adjustment[1:] = np.diff(self.spb_bca)

    def _apply_lower_spb(self):
        """
        Apply lower_spb scenario
        """
        # If 4-year adjustment period, spb_bca decreases by 0.5 for 2 years after adjustment period, if 7-year for 3 years
        lower_spb_adjustment_period = int(np.floor(self.adjustment_period / 2))
        for t in range(self.adjustment_end + 1, self.projection_period):
            if t <= self.adjustment_end + lower_spb_adjustment_period:
                self.spb_bca[t] -= 0.5 / lower_spb_adjustment_period * (t - self.adjustment_end)
            else:
                self.spb_bca[t] = self.spb_bca[t - 1]

    def _calculate_growth_policy_cost(self):
        """
        Calculate cost of growth policy
        """
        for t in range(self.adjustment_start, self.projection_period):

            # During growth policy period, cost is phased in
            if t < self.adjustment_start + self.growth_policy_period:
                self.growth_policy_cost_inflated[t] = self.growth_policy_cost * (t - self.adjustment_start + 1) / self.growth_policy_period

            # After growth policy period, cost stays constant
            else:
                self.growth_policy_cost_inflated[t] = self.growth_policy_cost

            # Inflate costs with nominal growth rate and calculate as share of NGDP
            for ng_value in self.ng[:t]:
                self.growth_policy_cost_inflated[t] *= 1 + ng_value / 100

            self.growth_policy_cost_ratio[t] = self.growth_policy_cost_inflated[t] / self.ngdp[t] * 100

    def _project_market_rate(self):
        """
        Project market rate data, needs to be in projection method because of scenario parameter.
        Uses BBG forward rates up to T+10, then linearly interpolates to long-term values.
        """
        # Clean vectors in case of repeated projection with different scenarios
        self.i_st[2:] = np.nan
        self.i_lt[2:] = np.nan

        # Set T + 10 value as market fwd rate
        self.i_st[10] = self.fwd_rate_st
        self.i_lt[10] = self.fwd_rate_lt

        # Set t + 30 values
        if self.country in ['POL', 'ROU']: self.i_lt[30:] = 4.5
        elif self.country in ['HUN']: self.i_lt[30:] = 5
        else: self.i_lt[30:] = 4

        yield_curve_coef = 0.5
        self.i_st[30:] = self.i_lt[30] * yield_curve_coef

        # Interpolate missing values
        x_st = np.arange(len(self.i_st))
        mask_st = np.isnan(self.i_st)
        self.i_st[mask_st] = np.interp(x_st[mask_st], x_st[~mask_st], self.i_st[~mask_st])

        x_lt = np.arange(len(self.i_lt))
        mask_lt = np.isnan(self.i_lt)
        self.i_lt[mask_lt] = np.interp(x_lt[mask_lt], x_lt[~mask_lt], self.i_lt[~mask_lt])

        if self.scenario == 'adverse_r_g':
            self._apply_adverse_r()

    def _apply_adverse_r(self):
        """
        Applies adverse interest rate conditions for adverse r-g scenario
        """
        self.i_st[self.adjustment_end + 1:] += 0.5
        self.i_lt[self.adjustment_end + 1:] += 0.5

    def _project_gdp(self):
        """
        Project nominal GDP.
        """
        for t in range(1, self.projection_period):
            self._calculate_rgdp(t)
            self._calculate_ngdp(t)

    def _calculate_rgdp(self, t):
        """
        Calcualtes real GDP and real growth
        """
        # Fiscal multiplier effect from change in SPB relative to baseline
        self.fm_effect[t] = self.fiscal_multiplier * ((self.spb_bca[t] - self.spb_bca[t - 1]) - (self.spb_bl[t] - self.spb_bl[t - 1]))

        # Fiscal multiplier effect on output gap
        self.output_gap[t] = self.output_gap_bl[t] - self.fm_effect[t] - 2 / 3 * self.fm_effect[t - 1] - 1 / 3 * self.fm_effect[t - 2]

        # Real growth and real GDP
        self.rgdp[t] = (self.output_gap[t] / 100 + 1) * self.rgdp_pot[t]
        self.rg[t] = (self.rgdp[t] - self.rgdp[t - 1]) / self.rgdp[t - 1] * 100

    def _calculate_ngdp(self, t):
        """
        Calcualtes nominal GDP and nominal growth
        """
        # Before adjustment period, nominal growth is baseline
        if t < self.adjustment_start:
            self.ng[t] = self.ng_bl[t]
            self.ngdp[t] = self.ngdp_bl[t]

        # After adjustment period, nominal growth based on real growth and inflation
        elif t >= self.adjustment_start:
            self.ng[t] = (1 + self.rg[t] / 100) * (1 + self.pi[t] / 100) * 100 - 100

            # Adjust nominal growth for adverse r-g scenario
            if self.scenario == 'adverse_r_g' and t > self.adjustment_end:
                self._apply_adverse_g(t)

            # project nominal GDP
            self.ngdp[t] = self.ngdp[t - 1] * (1 + self.ng[t] / 100)

    def _apply_adverse_g(self, t):
        """
        Applies adverse growth conditions for adverse r-g scenario
        """
        self.ng[t] -= 0.5

    def _project_stock_flow(self):
        """
        Calculate stock-flow adjustment as share of NGDP
        For specification of exceptions see DSM2023
        """
        for t in range(self.projection_period):

            # For Luxembourg, Finland stock flow is extended beyond T+2 using pension balance ratio
            if self.country in ['LUX', 'FIN']:
                
                if t < 3:
                    self.sf[t] = self.SF[t] / self.ngdp[t] * 100

                # From T+3 to T+10 apply percentage change of pension balance ratio
                if t >= 3 and t <= 10:
                    self.sf[t] = self.pension_balance_ratio[t]

                # For Finland linearly interpolate to 0 from T+11 to T+20
                elif self.country == 'FIN' and t > 10 and t <= 20:
                    self.sf[t] = self.sf[10] - (t - 10) * self.sf[10] / 10

                # For Luxembourg, linearly interpolate to 0 from T+11 to T+24
                elif self.country == 'LUX' and t > 10 and t <= 24:
                    self.sf[t] = self.sf[10] - (t - 10) * self.sf[10] / 14

            # For Greece stock-flow is based on deferal of ESM/EFSF interest payments
            elif self.country == 'GRC':

                # Stock flow is 5.4% in 2022
                if t == 0:
                    self.sf[t] = - 5.4

                # Increases to 11.1% in 2032 in cumulative terms
                elif t > 0 and t <= 9:
                    self.sf[t] = (- (11.1 / 100 * self.ngdp[9] 
                                     + np.sum(self.SF[:t])) 
                                     / (10-t) 
                                     / self.ngdp[t] * 100)

                # Decline to zero by projection end, 2070
                elif t > 9: 
                    self.sf[t] = (- np.sum(self.SF[:10]) 
                                  / (self.projection_period - 9) 
                                  / self.ngdp[t] * 100)
            
            # For other countries stock flow is simply based on Ameco data
            else:
                self.sf[t] = self.SF[t] / self.ngdp[t] * 100

            # Project SF for all countries
            self.SF[t] = self.sf[t] / 100 * self.ngdp[t]
            

    def _project_spb(self):
        """
        Project structural primary balance
        """
        for t in range(1, self.projection_period):

            # Ageing cost adjustments are accounted for by spb adjustment during the adjustment period
            if t <= self.adjustment_end:
                self.spb[t] = self.spb_bca[t]

            # After adjustment period ageing costs affect the SPB for duration of "ageing_cost_period"
            elif t > self.adjustment_end and t <= self.adjustment_end + self.ageing_cost_period:
                self.ageing_component[t] = - (self.ageing_cost[t] - self.ageing_cost[self.adjustment_end])
                self.spb[t] = self.spb_bca[t] + self.ageing_component[t]

            # After ageing cost period, SPB is baseline
            elif t > self.adjustment_end + self.ageing_cost_period:
                self.spb[t] = self.spb[t - 1]

            # Total SPB for calcualtion of structural deficit
            self.SPB[t] = self.spb[t] / 100 * self.ngdp[t]

    def _project_pb(self):
        """
        Project primary balance adjusted as sum of SPB, cyclical component, and property income component
        """
        for t in range(self.projection_period):

            # Calculate components
            self.output_gap[t] = (self.rgdp[t] / self.rgdp_pot[t] - 1) * 100
            self.cyclical_component[t] = self.budget_balance_elasticity * self.output_gap[t]
            # self.property_income_component[t] = self.property_income[t] - self.property_income[self.adjustment_start - 1]

            # Calculate primary balance ratio as sum of components and total primary balance
            self.pb[t] = self.spb[t] + self.cyclical_component[t] # + self.property_income_component[t]
            self.PB[t] = self.pb[t] / 100 * self.ngdp[t]

    def _project_debt_ratio(self):
        """
        Main loop for debt dynamics
        """
        for t in range(1, self.projection_period):

            # Apply financial stress scenario if specified
            if self.scenario == 'financial_stress' and t == self.adjustment_end + 1:
                self._apply_financial_stress(t)

            # Calculate implicit interest rate, interestst, repayments, gross financing needs, debt stock, overall balance, and debt ratio
            self._calculate_iir(t)
            self._calculate_interest(t)
            self._calculate_repayment(t)
            self._calculate_gfn(t)
            self._calculate_debt_stock(t)
            self._calculate_balance(t)
            self._calculate_debt_ratio(t)

    def _apply_financial_stress(self, t):
        """
        Adjust interest rates for financial stress scenario
        """
        # Adjust market rates for high debt countries financial stress scenario
        if self.d[self.adjustment_end] > 90:
            self.i_st[t] += (1 + (self.d[self.adjustment_end] - 90) * 0.06)
            self.i_lt[t] += (1 + (self.d[self.adjustment_end] - 90) * 0.06)

        # Adjust market rates for low debt countries financial stress scenario
        else:
            self.i_st[t] += 1
            self.i_lt[t] += 1

    def _calculate_iir(self, t):
        """
        Calculate implicit interest rate
        """
        # Calculate the shares of short term and long term debt in total debt
        self.alpha[t - 1] = self.D_st[t - 1] / self.D[t - 1]
        self.beta[t - 1] = self.D_new_lt[t - 1] / self.D_lt[t - 1]

        # Use ameco implied interest until T+3 and back out iir_lt
        if t <= 2:
            self.iir_lt[t] = (self.iir[t] - self.alpha[t - 1] * self.i_st[t]) / (1 - self.alpha[t - 1])
            self.iir[t] = self.iir_bl[t]

        # Use DSM 2023 Annex A3 formulation after
        else:
            self.iir_lt[t] = self.beta[t - 1] * self.i_lt[t] + (1 - self.beta[t - 1]) * self.iir_lt[t - 1]
            self.iir[t] = self.alpha[t - 1] * self.i_st[t] + (1 - self.alpha[t - 1]) * self.iir_lt[t]

        # Replace all 10 < iir < 0 with previous period value
        for iir in [self.iir, self.iir_lt]:
            if iir[t] < 0 or iir[t] > 10 or np.isnan(iir[t]):
                iir[t] = iir[t - 1]

    def _calculate_interest(self, t):
        """
        Calculate interest payments on newly issued debt
        """
        self.interest_st[t] = self.D_st[t - 1] * self.i_st[t - 1] / 100  # interest payments on newly issued short-term debt
        self.interest_lt[t] = self.iir_lt[t] / 100 * self.D_lt[t - 1]  # lt interest is t-1 lt debt times implicit lt interest rate
        self.interest[t] = self.interest_st[t] + self.interest_lt[t]  # interest payments on newly issued debt and outstanding legacy debt
        self.interest_ratio[t] = self.interest[t] / self.ngdp[t] * 100

    def _calculate_repayment(self, t):
        """
        Calculate repayment of newly issued debt
        """
        self.repayment_st[t] = self.D_st[t - 1]  # repayment payments on short-term debt share in last years gross financing needs
        self.repayment_lt[t] = self.D_share_lt_maturing[t] * self.D_lt[t - 1] + self.repayment_lt_esm[t]  # lt repayment based on maturing share and inst debt
        self.repayment[t] = self.repayment_st[t] + self.repayment_lt[t]  # repayment of newly issued st, lt debt

    def _calculate_gfn(self, t):
        """
        Calculate gross financing needs
        """
        self.GFN[t] = np.max([self.interest[t] + self.repayment[t] - self.PB[t] + self.SF[t], 0])

    def _calculate_debt_stock(self, t):
        """
        Calculate new debt stock and distribution of new short and long-term issuance
        """
        # Total debt stock is equal to last period stock minus repayment plus financing needs
        self.D[t] = np.max([self.D[t - 1] - self.repayment[t] + self.GFN[t], 0])

        # Distribution of short-term and long-term debt in financing needs
        D_stn_theoretical = self.D_share_st * self.D[t]  # st debt to keep share equal to D_share_st
        D_new_lt_theoretical = (1 - self.D_share_st) * self.D[t] - self.D_lt[t - 1] + self.repayment_lt[t]  # lt debt to keep share equal to 1 - D_share_st
        D_share_st_issuance = D_stn_theoretical / (D_stn_theoretical + D_new_lt_theoretical)  # share of st in gfn

        # Calculate short-term and long-term debt issuance
        self.D_st[t] = D_share_st_issuance * self.GFN[t]
        self.D_new_lt[t] = (1 - D_share_st_issuance) * self.GFN[t]
        self.D_lt[t] = self.D_lt[t - 1] - self.repayment_lt[t] + self.D_new_lt[t]

    def _calculate_balance(self, t):
        """
        Calculate overall balance and structural fiscal balance
        """
        self.ob[t] = (self.PB[t] - self.interest[t]) / self.ngdp[t] * 100
        self.sb[t] = (self.SPB[t] - self.interest[t]) / self.ngdp[t] * 100

    def _calculate_debt_ratio(self, t):
        """
        Calculate debt ratio (zero floor)
        """
        self.d[t] = np.max([
            self.D_share_domestic * self.d[t - 1] * (1 + self.iir[t] / 100) / (1 + self.ng[t] / 100)
            + self.D_share_eur * self.d[t - 1] * (1 + self.iir[t] / 100) / (1 + self.ng[t] / 100) * (self.exr_eur[t] / self.exr_eur[t - 1])
            + self.D_share_usd * self.d[t - 1] * (1 + self.iir[t] / 100) / (1 + self.ng[t] / 100) * (self.exr_usd[t] / self.exr_usd[t - 1])
            - self.pb[t] + self.sf[t], 0
        ])
        
# ========================================================================================= #
#                               OPTIMIZATION METHODS                                        #
# ========================================================================================= #

    def find_edp(self, spb_target=None):
        """
        Find the number of periods needed to correct an excessive deficit if possible within adjustment period.
        """
        # Project baseline and check if deficit is excessive
        if spb_target is None:
            self.spb_target = None
        else:
            self.spb_target = spb_target
        self.project(spb_target=spb_target)

        # Define EDP threshold, set to 3% of GDP
        self.edp_target = np.full(self.adjustment_period, -3, dtype=float)

        # If deficit excessive, increase spb by 0.5 annually until deficit below 3%
        if self.ob[self.adjustment_start] < self.edp_target[0]:

            # Set start indices for spb and pb adjustment parts of EDP
            self.edp_spb_index = 0
            self.edp_sb_index = 3

            # Calculate EDP adjustment steps for spb, sb, and final periods
            self._calculate_edp_spb()
            self._calculate_edp_sb()
            self._calculate_edp_end(spb_target=spb_target)

        # If excessive deficit in year before adjustment start, set edp_end to adjustment start
        elif self.ob[self.adjustment_start - 1] < self.edp_target[0]:
            self.edp_period = 0
            self.edp_end = self.adjustment_start
            
        # If deficit not excessive, set EDP period to 0
        else:
            self.edp_period = 0
            self.edp_end = self.adjustment_start - 1

    def _save_edp_period(self):
        """
        Saves EDP period and end period
        """
        self.edp_period = np.where(~np.isnan(self.edp_steps))[0][-1] + 1
        self.edp_end = self.adjustment_start + self.edp_period        

    def _calculate_edp_spb(self):
        """
        Calculate EDP adjustment steps ensuring minimum strucutral primary balance adjustment
        """
        # Loop for SPB part of EDP: min. 0.5 spb adjustment while deficit > 3 and in spb adjustmet period
        while (self.ob[self.adjustment_start + self.edp_spb_index] < self.edp_target[self.edp_spb_index]
                and self.edp_spb_index < self.edp_sb_index):
            # Set EDP step to 0.5
            self.edp_steps[self.edp_spb_index] = 0.5

            # Project using last periods SPB as target, move to next period
            self.project(
                spb_target=self.spb_target,
                edp_steps=self.edp_steps
            )
            self.edp_spb_index += 1
            self._save_edp_period()

    def _calculate_edp_sb(self):
        """
        Calculate EDP adjustment steps ensuring minimum strucutral balance adjustment
        """
        # Loop for SB balance part of EDP: min. 0.5 ob adjustment while deficit > 3 and before last period
        while (self.ob[self.adjustment_start + self.edp_sb_index] < self.edp_target[self.edp_sb_index]
                and self.edp_sb_index + 1 < self.adjustment_period):
            print(self.edp_sb_index, self.ob[self.adjustment_start + self.edp_sb_index])
            
            # If sb adjustment is less than 0.5, increase by 0.001
            while (self.sb[self.adjustment_start + self.edp_sb_index] 
                   - self.sb[self.adjustment_start + self.edp_sb_index - 1] < 0.5):
            
                # Initiate sb step at current adjustment_step value, increase by 0.001
                self.edp_steps[self.edp_sb_index] = self.adjustment_steps[self.edp_sb_index]
                self.edp_steps[self.edp_sb_index] += 0.001

                # Project using last periods SPB as target, move to next period
                self.project(
                    spb_target=self.spb_target,
                    edp_steps=self.edp_steps
                )
                self._save_edp_period()

            # If sb adjustment reaches min. 0.5, move to next period
            if self.sb[self.adjustment_start + self.edp_sb_index] - self.sb[self.adjustment_start + self.edp_sb_index - 1] >= 0.5:
                self.edp_sb_index += 1

    def _calculate_edp_end(self, spb_target):
        """
        Calculate EDP adjustment steps or SPB target ensuring deficit below 3% at adjustment end
        """
        # If EDP lasts until penultimate adjustmet period, increase EDP steps to ensure deficit < 3
        if self.edp_period == self.adjustment_period:
            while self.ob[self.adjustment_end] <= self.edp_target[-1]:

                # Aim for linear adjustment path by increasing smallest EDP steps first
                min_edp_steps = np.min(self.edp_steps[~np.isnan(self.edp_steps)])
                min_edp_indices = np.where(self.edp_steps == min_edp_steps)[0]
                self.edp_steps[min_edp_indices] += 0.001
                self.project(
                    spb_target=self.spb_target,
                    edp_steps=self.edp_steps
                )
                self._save_edp_period()

        # If last EDP period has deficit < 3, we do not impose additional adjustment
        if self.ob[self.adjustment_start - 1 + self.edp_period] >= self.edp_target[-1]:
            self.edp_steps[self.edp_sb_index:] = np.nan
            self._save_edp_period()

        # If no spb_target was specified, calculate to ensure deficit < 3 until adjustment end
        if spb_target is None:
            print('No SPB target specified, calculating to ensure deficit < 3')
            while np.any(self.ob[self.edp_end:self.adjustment_end + 1] <= self.edp_target[-1]):
                self.spb_target += 0.001
                self.project(spb_target=self.spb_target, edp_steps=self.edp_steps)

    def find_spb_deterministic(self, criterion, bounds=(-10, 10), steps=[0.01, 0.0001]):
        """
        Find the primary balance that ensures complience with deterministic criteria
        """
        # Check if input parameter correctly specified
        assert criterion in [
            None,
            'main_adjustment',
            'lower_spb',
            'financial_stress',
            'adverse_r_g',
            'deficit_reduction',
            'debt_safeguard',
        ], 'Unknown deterministic criterion'

        # Set scenario parameter
        if criterion in [None, 'main_adjustment', 'debt_safeguard']:
            self.scenario = 'main_adjustment'
        else:
            self.scenario = criterion

        # Precalculate EDP for debt safeguard if not specified and call optimizer
        if not hasattr(self, 'edp_steps'):
            if criterion == 'debt_safeguard':
                print('Precalculating EDP steps for debt safeguard')
                self.find_edp()
            else:
                self.edp_steps = None

        # If predefined adjustment steps are specified, project with them 
        if hasattr(self, 'predefined_adjustment_steps'):
            self.project(
                edp_steps=self.edp_steps,
                adjustment_steps=np.nan_to_num(self.predefined_adjustment_steps),
                scenario=self.scenario
            )

        # Run deterministic optimization
        return self._deterministic_optimization(criterion=criterion, bounds=bounds, steps=steps)

    def _deterministic_optimization(self, criterion, bounds, steps):  # TODO find error
        """
        Main loop of optimizer for debt safeguard
        """
        # If debt safeguard and EDP lasts until penultimate adjustment year, debt safeguard satisfied by default
        if (criterion == 'debt_safeguard'
                and self.edp_period >= self.adjustment_period - 1):
            self.spb_target = self.spb_bca[self.edp_end - 1]
            self.project(
                spb_target=self.spb_target,
                edp_steps=self.edp_steps
            )
            return self.spb_target

        # Initialize spb_target to the lower bound
        spb_target = bounds[0]

        # Optimization loop
        while spb_target <= bounds[1]:
            try:
                # Project the model with the current spb_target
                self._get_adjustment_steps(criterion=criterion, spb_target=spb_target,)
                self.project(
                    edp_steps=self.edp_steps,
                    adjustment_steps=self.adjustment_steps,
                    scenario=self.scenario
                )

                # If condition is met, enter nested loop and decrease spb_target in small steps
                if self._deterministic_condition(criterion=criterion):
                    while (self._deterministic_condition(criterion=criterion)
                           and spb_target >= bounds[0]):
                        current_spb_target = spb_target
                        spb_target -= steps[1]
                        self._get_adjustment_steps(criterion=criterion, spb_target=spb_target)
                        self.project(
                            edp_steps=self.edp_steps,
                            adjustment_steps=self.adjustment_steps,
                            scenario=self.scenario
                        )
                    break

                # If condition is not met, increase spb_target in large steps
                current_spb_target = spb_target
                spb_target += steps[0]

            except BaseException:
                raise  # Exception(f'No solution found for {criterion}')

        # If spb_target exceeds upper bound, raise exception
        if spb_target > bounds[1] - steps[1]:
            raise  # Exception(f'No solution found for {criterion}')

        # Return last valid spb_target as optimal spb and project with target
        self.spb_target = current_spb_target
        spb_target -= steps[1]
        self._get_adjustment_steps(criterion=criterion, spb_target=spb_target)

        return self.spb_bca[self.adjustment_end]

    def _get_adjustment_steps(self, criterion, spb_target):
        """
        Get adjustment steps for debt safeguard after EDP
        """
        # If debt safeguard, apply adjustment to period after EDP
        if criterion == 'debt_safeguard':
            num_steps = self.adjustment_period - self.edp_period
            step_size = (spb_target - self.spb_bca[self.edp_end - 1]) / num_steps
            non_edp_steps = np.full(num_steps, step_size)
            edp_steps_nonan = self.edp_steps[~np.isnan(self.edp_steps)]
            self.adjustment_steps = np.concatenate([edp_steps_nonan, non_edp_steps])

        # If adjustment steps are predifined, use them
        if hasattr(self, 'predefined_adjustment_steps'):
            self.adjustment_steps = np.copy(self.predefined_adjustment_steps)
            last_non_nan = np.where(~np.isnan(self.predefined_adjustment_steps))[0][-1]
            num_steps = self.adjustment_period - (last_non_nan + 1)
            step_size = (spb_target - self.spb_bca[self.adjustment_start+last_non_nan]) / num_steps
            self.adjustment_steps[last_non_nan+1:] = np.full(num_steps, step_size)

        # Otherwise apply adjustment to all periods
        else:
            num_steps = self.adjustment_period
            step_size = (spb_target - self.spb_bca[self.adjustment_start - 1]) / num_steps
            self.adjustment_steps = np.full(num_steps, step_size)

    def _deterministic_condition(self, criterion):
        """
        Defines deterministic criteria and checks if they are met.
        """
        if (criterion == 'main_adjustment'
            or criterion == 'lower_spb'
            or criterion == 'financial_stress'
            or criterion == 'adverse_r_g'):
            return self._debt_decline_criterion()
        elif criterion == 'deficit_reduction':
            return self._deficit_reduction_criterion()
        elif criterion == 'debt_safeguard':
            return self._debt_safeguard_criterion()
        else:
            return False

    def _debt_decline_criterion(self):
        """
        Checks the debt decline criterion from adjustment end to 10 years after adjustment end.
        """
        return (np.all(np.diff(self.d[self.adjustment_end:self.adjustment_end + 11]) < 0)
                or self.d[self.adjustment_end + 10] <= 60)

    def _deficit_reduction_criterion(self):
        """
        Checks the deficit reduction criterion for <3% deficit for 10 years after adjustment end.
        """
        return np.all(self.ob[self.adjustment_end:self.adjustment_end + 11] >= -3)

    def _debt_safeguard_criterion(self):
        """
        Checks the debt safeguard criterion.
        """
        debt_safeguard_decline = 1 if self.d[self.adjustment_start - 1] > 90 else 0.5

        return (self.d[self.edp_end] - self.d[self.adjustment_end]
                >= debt_safeguard_decline * (self.adjustment_end - self.edp_end))

    def find_spb_deficit_resilience(self):
        """
        Apply the deficit resilience targets that sets min. annual spb adjustment if structural deficit exceeds 1.5%.
        """
        # Initialize deficit_resilience_steps
        self.deficit_resilience_steps = np.full((self.adjustment_period,), np.nan, dtype=np.float64)

        # Define structural deficit target
        self.deficit_resilience_target = np.full(self.adjustment_period, -1.5, dtype=float)

        # Define deficit resilience step size
        if self.adjustment_period == 4:
            self.deficit_resilience_step = 0.4
        elif self.adjustment_period == 7:
            self.deficit_resilience_step = 0.25

        # Project baseline
        self.project(
            spb_target=self.spb_target,
            edp_steps=self.edp_steps,
            deficit_resilience_steps=self.deficit_resilience_steps
        )

        self.deficit_resilience_start = self.adjustment_start

        # Run deficit resilience loop
        self._deficit_resilience_loop_adjustment()

        return self.spb_bca[self.adjustment_end]

    def _deficit_resilience_loop_adjustment(self):
        """
        Loop for adjustment period violations of deficit resilience
        """
        for t in range(self.deficit_resilience_start, self.adjustment_end + 1):
            if ((self.d[t] > 60 or self.ob[t] < -3)
                and self.sb[t] <= self.deficit_resilience_target[t - self.adjustment_start] 
                and self.adjustment_steps[t - self.adjustment_start] < self.deficit_resilience_step - 1e-8):  # 1e-8 tolerance for floating point errors
                self.deficit_resilience_steps[t - self.adjustment_start] = self.adjustment_steps[t - self.adjustment_start]
                while (self.sb[t] <= self.deficit_resilience_target[t - self.adjustment_start]
                       and self.deficit_resilience_steps[t - self.adjustment_start] < self.deficit_resilience_step - 1e-8):  # 1e-8 tolerance for floating point errors
                    self.deficit_resilience_steps[t - self.adjustment_start] += 0.001
                    self.project(
                        spb_target=self.spb_target,
                        edp_steps=self.edp_steps,
                        deficit_resilience_steps=self.deficit_resilience_steps
                    )

    def find_spb_deficit_resilience_post_adjustment(self):
        """
        Apply the post-adjustment targets that sets min. annual spb adjustment if structural deficit exceeds 1.5%.
        """
        # Set nan deficit steps during adjusmtent period if not defined
        if not hasattr(self, 'deficit_resilience_steps'):
            print('No deficit resilience steps defined')
            self.deficit_resilience_steps = np.full((self.adjustment_period,), np.nan, dtype=np.float64)

        # Define deficit resilience step size
        if self.adjustment_period == 4:
            self.deficit_resilience_step = 0.4
        elif self.adjustment_period == 7:
            self.deficit_resilience_step = 0.25

        # Initialize post_adjustment_steps
        self.post_adjustment_steps = np.full((self.projection_period - self.adjustment_end - 1,), np.nan, dtype=np.float64)

        # Define post-adjustment target
        self.post_adjustment_target = -1.5

        # Define post-adjustment step size
        if self.adjustment_period == 4:
            self.post_adjustment_step = 0.4
        elif self.adjustment_period == 7:
            self.post_adjustment_step = 0.25

        # Project baseline
        self.project(
            spb_target=self.spb_target,
            edp_steps=self.edp_steps,
            deficit_resilience_steps=self.deficit_resilience_steps
        )

        # Apply post-adjustment loop
        self._deficit_resilience_loop_post_adjustment()

        return self.spb_bca[self.adjustment_end]

    def _deficit_resilience_loop_post_adjustment(self):
        """
        Loop for post-adjustment period violations of deficit resilience
        """
        for t in range(self.adjustment_end + 1, self.adjustment_end + 11):
            if ((self.d[t] > 60 or self.ob[t] < -3)
                and self.sb[t] <= self.post_adjustment_target):
                while (self.sb[t] <= self.post_adjustment_target
                        and self.post_adjustment_steps[t - self.adjustment_end - 1] < self.deficit_resilience_step - 1e-8):  # 1e-8 tolerance for floating point errors
                    self.post_adjustment_steps[t - self.adjustment_end - 1] += 0.001
                    self.project(
                        spb_target=self.spb_target,
                        edp_steps=self.edp_steps,
                        deficit_resilience_steps=self.deficit_resilience_steps,
                        post_adjustment_steps=self.post_adjustment_steps
                    )
    
# ========================================================================================= #
#                                   AUXILIARY METHODS                                       #
# ========================================================================================= #

    def df(self, *vars, all=False):
        """
        Return a dataframe with the specified variables as columns and years as rows.
        Takes a variable name (string) or a list of variable names as input.
        Alternatively takes a dictionary as input, where keys are variables (string) and values are variable names.
        """
        # if no variables specified, return spb, ob, d
        if not vars and all == False:
            vars = ['d', 'ob', 'sb', 'spb_bca', 'spb_bca_adjustment']

        # if all option True specified, return all variables
        elif not vars and all:
            vars = ['d',  # debt ratio
                    'spb_bca',  # ageing-cost adjusted structural primary balance
                    'spb_bca_adjustment',  # adjustment to ageing-cost adjusted structural primary balance
                    'spb',  # structural primary balance
                    'pb',  # primary balance
                    'ob',  # overall balance
                    'sb',  # structural balance
                    'ageing_component',  # ageing component of primary balance
                    'cyclical_component',  # cyclical component of primary balance
                    'interest_ratio',  # interest payments as share of GDP
                    'ageing_cost',  # ageing cost
                    'rg',  # real GDP growth
                    'rg_pot',  # potential real GDP growth
                    'ng',  # nominal GDP growth
                    'output_gap',  # output gap
                    'pi',  # inflation
                    'rgdp_pot',  # potential real GDP
                    'rgdp',  # real GDP
                    'ngdp',  # nominal GDP
                    'i_st',  # short-term interest rate
                    'i_lt',  # long-term interest rate
                    'iir_lt',  # implicit long-term interest rate
                    'iir',  # implicit interest rate
                    'sf',  # stock flow adjustment
                    'D',  # debt level
                    'D_lt_esm',  # long-term instirutional debt level
                    'D_st',  # short-term debt level
                    'D_lt',  # long-term debt level
                    'repayment',  # repayment
                    'repayment_lt',  # long-term repayment
                    'repayment_lt_esm',  # long-term institutional repayment
                    'interest',  # interest payments
                    'interest_lt',  # long-term interest payments
                    'interest_st',  # short-term interest payments
                    ]

        # If given dictionary as input, convert to list of variables and variable names
        if isinstance(vars[0], dict):
            var_dict = vars[0]
            var_names = list(var_dict.values())
            vars = list(var_dict.keys())

        # If given list as input, convert to list of variables and variable names
        elif isinstance(vars[0], list):
            vars = vars[0]
            var_names = None
        else:
            var_names = None

        var_values = [getattr(self, var) if isinstance(var, str) else var for var in vars]

        df = pd.DataFrame(
            {vars[i]: var for i, var in enumerate(var_values)},
            index=range(self.start_year, self.end_year + 1)
        )

        if var_names:
            df.columns = var_names
        df.reset_index(names='y', inplace=True)
        df.reset_index(names='t', inplace=True)
        df.set_index(['t', 'y'], inplace=True)

        return df
