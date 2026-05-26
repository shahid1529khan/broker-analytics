import logging

logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from collections import defaultdict
from backend.db.supabase_client import get_supabase

def _parse_period(period_str: str) -> date:
    """Parses 'YYYY-MM' into a date object representing the first of the month."""
    year, month = period_str.split('-')
    return date(int(year), int(month), 1)

def _get_months_diff(date1: date, date2: date) -> int:
    return (date1.year - date2.year) * 12 + date1.month - date2.month

def get_client_loan_rows(client_id: str, periods: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Fetches all loan rows for a client, optionally filtered by specific period_months."""
    try:
        supabase = get_supabase()
        query = supabase.table('loan_rows').select('*').eq('client_id', client_id)
        if periods:
            query = query.in_('period_month', periods)
        
        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error fetching loan rows for client {client_id}: {e}")
        return []

class AnalyticsEngine:
    def __init__(self, client_id: str, periods: Optional[List[str]] = None):
        self.client_id = client_id
        # Data is sorted by period_month chronologically
        # Loads all rows for client into memory. 
        # For books above ~50,000 rows, push aggregation into SQL instead.
        raw_rows = get_client_loan_rows(client_id, periods)
        self.rows = sorted(raw_rows, key=lambda x: x['period_month'])
        
        # Group rows by period
        self.periods_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in self.rows:
            self.periods_data[row['period_month']].append(row)
            
        self.sorted_periods = sorted(self.periods_data.keys())

    # 2.1 Loan age analysis
    def get_loan_age_analysis(self) -> Dict[str, Any]:
        """
        Groups loans into age buckets and provides shift over time for charting.
        Expected chart shape: 
        [{ name: '2023-01', '0-12m': 500000, '13-24m': ... }, ...]
        """
        trend_data = []
        latest_period_breakdown = {}
        
        for period in self.sorted_periods:
            period_date = _parse_period(period)
            buckets_balance = {'0-12m': 0, '13-24m': 0, '25-36m': 0, '37-60m': 0, '60+m': 0}
            buckets_count = {'0-12m': 0, '13-24m': 0, '25-36m': 0, '37-60m': 0, '60+m': 0}
            
            for row in self.periods_data[period]:
                settlement_str = row.get('settlement_date')
                if not settlement_str:
                    continue # Cannot compute age
                
                try:
                    settlement_date = date.fromisoformat(settlement_str)
                    age_months = _get_months_diff(period_date, settlement_date)
                except ValueError:
                    continue
                
                balance = row.get('outstanding_balance', 0.0)
                
                if age_months <= 12:
                    bucket = '0-12m'
                elif age_months <= 24:
                    bucket = '13-24m'
                elif age_months <= 36:
                    bucket = '25-36m'
                elif age_months <= 60:
                    bucket = '37-60m'
                else:
                    bucket = '60+m'
                    
                buckets_balance[bucket] += balance
                buckets_count[bucket] += 1
                
            period_trend = {"name": period, **buckets_balance}
            trend_data.append(period_trend)
            
            if period == self.sorted_periods[-1]:
                latest_period_breakdown = {
                    "balances": buckets_balance,
                    "counts": buckets_count
                }
                
        return {
            "trend_data": trend_data, # For Stacked Bar Chart
            "latest_breakdown": latest_period_breakdown
        }

    # 2.2 Average loan size
    def get_average_loan_size(self) -> Dict[str, Any]:
        trend_data = []
        latest_lender_averages = {}
        overall_average = 0.0
        
        for period in self.sorted_periods:
            rows = self.periods_data[period]
            total_bal = sum(r.get('outstanding_balance', 0.0) for r in rows)
            count = len(rows)
            avg_size = (total_bal / count) if count > 0 else 0.0
            
            trend_data.append({
                "period": period,
                "average_size": avg_size
            })
            
            if period == self.sorted_periods[-1]:
                overall_average = avg_size
                
                lender_sums = defaultdict(float)
                lender_counts = defaultdict(int)
                for r in rows:
                    lender = r.get('lender_name', 'Unknown')
                    lender_sums[lender] += r.get('outstanding_balance', 0.0)
                    lender_counts[lender] += 1
                    
                for lender in lender_sums:
                    latest_lender_averages[lender] = lender_sums[lender] / lender_counts[lender]
                    
        return {
            "trend_data": trend_data,
            "overall_average": overall_average,
            "lender_averages": latest_lender_averages
        }

    # 2.3 Lender concentration
    def get_lender_concentration(self) -> Dict[str, Any]:
        if not self.sorted_periods:
            return {"chart_data": [], "ranked_table": [], "concentration_risks": []}
            
        latest_period = self.sorted_periods[-1]
        rows = self.periods_data[latest_period]
        
        total_book = sum(r.get('outstanding_balance', 0.0) for r in rows)
        lender_stats = defaultdict(lambda: {"balance": 0.0, "count": 0})
        
        for r in rows:
            lender = r.get('lender_name', 'Unknown')
            lender_stats[lender]["balance"] += r.get('outstanding_balance', 0.0)
            lender_stats[lender]["count"] += 1
            
        ranked = []
        risks = []
        chart_data = []
        
        for lender, stats in lender_stats.items():
            pct = (stats["balance"] / total_book * 100) if total_book > 0 else 0.0
            item = {
                "lender_name": lender,
                "total_balance": stats["balance"],
                "loan_count": stats["count"],
                "percentage": round(pct, 2)
            }
            ranked.append(item)
            chart_data.append({"name": lender, "value": stats["balance"]})
            
            if pct > 30.0:
                risks.append(lender)
                
        ranked.sort(key=lambda x: x["total_balance"], reverse=True)
        chart_data.sort(key=lambda x: x["value"], reverse=True)
        
        return {
            "chart_data": chart_data,
            "ranked_table": ranked,
            "concentration_risks": risks # Lenders > 30%
        }

    # 2.4 Trail income analysis
    def get_trail_income_analysis(self) -> Dict[str, Any]:
        trend_data = []
        cumulative = 0.0
        
        for i, period in enumerate(self.sorted_periods):
            rows = self.periods_data[period]
            trail_this_month = sum(r.get('trail_income_this_period', 0.0) for r in rows)
            cumulative += trail_this_month
            
            item = {
                "period": period,
                "trail_income": trail_this_month,
                "cumulative": cumulative,
                "mom_change_abs": 0.0,
                "mom_change_pct": 0.0,
                "yoy_change_pct": 0.0
            }
            
            if i > 0:
                prev_trail = trend_data[i-1]["trail_income"]
                item["mom_change_abs"] = trail_this_month - prev_trail
                if prev_trail > 0:
                    item["mom_change_pct"] = round((item["mom_change_abs"] / prev_trail) * 100, 2)
                    
            # Check YoY if 12 months prior exists
            if i >= 12:
                yoy_trail = trend_data[i-12]["trail_income"]
                if yoy_trail > 0:
                    item["yoy_change_pct"] = round(((trail_this_month - yoy_trail) / yoy_trail) * 100, 2)
                    
            trend_data.append(item)
            
        latest_lender_breakdown = []
        if self.sorted_periods:
            latest_rows = self.periods_data[self.sorted_periods[-1]]
            lenders = defaultdict(float)
            for r in latest_rows:
                lenders[r.get('lender_name', 'Unknown')] += r.get('trail_income_this_period', 0.0)
            latest_lender_breakdown = [{"name": k, "value": v} for k, v in lenders.items()]
            latest_lender_breakdown.sort(key=lambda x: x["value"], reverse=True)
            
        return {
            "trend_data": trend_data, # Line chart data
            "latest_lender_breakdown": latest_lender_breakdown
        }

    # 2.5 Run-off analysis
    def get_run_off_analysis(self) -> Dict[str, Any]:
        trend_data = []
        
        # Build lookup dicts per period: { loan_id or borrower_ref: balance }
        period_balances = {}
        for period in self.sorted_periods:
            pb = {}
            for row in self.periods_data[period]:
                # We need a unique identifier. loan_id is preferred, borrower_reference as fallback.
                # If both are null, fallback to a composite key to prevent silently dropping loans.
                uid = (row.get('loan_id') 
                       or row.get('borrower_reference') 
                       or f"{row.get('lender_name')}_{row.get('settlement_date')}_{row.get('loan_amount_original')}")
                if uid:
                    pb[uid] = {
                        "balance": row.get('outstanding_balance', 0.0),
                        "lender": row.get('lender_name', 'Unknown'),
                        "settlement_date": row.get('settlement_date')
                    }
            period_balances[period] = pb
            
        for i in range(len(self.sorted_periods) - 1):
            period_n = self.sorted_periods[i]
            period_next = self.sorted_periods[i+1]
            
            pb_n = period_balances[period_n]
            pb_next = period_balances[period_next]
            
            opening_balance = sum(v["balance"] for v in pb_n.values())
            balance_lost = 0.0
            
            for uid, info_n in pb_n.items():
                if uid not in pb_next:
                    balance_lost += info_n["balance"] # Loan closed
                else:
                    bal_diff = info_n["balance"] - pb_next[uid]["balance"]
                    if bal_diff > 0:
                        balance_lost += bal_diff # Partial pay-down / run-off
                        
            run_off_rate = (balance_lost / opening_balance * 100) if opening_balance > 0 else 0.0
            
            trend_data.append({
                "period": period_next, # Logged against the month it was realized
                "run_off_rate": round(run_off_rate, 2),
                "balance_lost": balance_lost,
                "annualised_run_off_rate": round(run_off_rate * 12, 2)
            })
            
        return {
            "trend_data": trend_data # For bar chart of monthly run-off rates
        }

    # 2.6 Loan book size over time
    def get_book_size_trend(self) -> Dict[str, Any]:
        trend_data = []
        
        for i, period in enumerate(self.sorted_periods):
            rows = self.periods_data[period]
            total_book = sum(r.get('outstanding_balance', 0.0) for r in rows)
            
            item = {
                "period": period,
                "total_balance": total_book,
                "net_change": 0.0
            }
            
            if i > 0:
                item["net_change"] = total_book - trend_data[i-1]["total_balance"]
                
            trend_data.append(item)
            
        growth_trend = "Stable"
        if len(trend_data) >= 6:
            early_avg = sum(t["total_balance"] for t in trend_data[:3]) / 3
            recent_avg = sum(t["total_balance"] for t in trend_data[-3:]) / 3
            if recent_avg > early_avg * 1.05:
                growth_trend = "Growing"
            elif recent_avg < early_avg * 0.95:
                growth_trend = "Declining"
        elif len(trend_data) >= 2:
            first = trend_data[0]["total_balance"]
            last = trend_data[-1]["total_balance"]
            if last > first * 1.05:
                growth_trend = "Growing"
            elif last < first * 0.95:
                growth_trend = "Declining"
                
        return {
            "trend_data": trend_data, # Area chart
            "growth_trend": growth_trend
        }

    # 2.7 Settlement history
    def get_settlement_history(self) -> Dict[str, Any]:
        trend_data = []
        
        first_seen: Dict[str, str] = {}  # uid -> period_month

        for period in self.sorted_periods:
            for r in self.periods_data[period]:
                uid = (r.get('loan_id') 
                       or r.get('borrower_reference') 
                       or f"{r.get('lender_name')}_{r.get('settlement_date')}_{r.get('loan_amount_original')}")
                if uid and uid not in first_seen:
                    first_seen[uid] = period
        
        for period in self.sorted_periods:
            rows = self.periods_data[period]
            new_loans_count = 0
            new_settlement_value = 0.0
            
            for r in rows:
                uid = (r.get('loan_id') 
                       or r.get('borrower_reference') 
                       or f"{r.get('lender_name')}_{r.get('settlement_date')}_{r.get('loan_amount_original')}")
                if uid and first_seen.get(uid) == period:
                    new_loans_count += 1
                    # Use original loan amount if available, fallback to balance
                    new_val = r.get('loan_amount_original') or r.get('outstanding_balance', 0.0)
                    new_settlement_value += new_val
                    
            trend_data.append({
                "period": period,
                "new_loans_count": new_loans_count,
                "new_settlement_value": new_settlement_value
            })
            
        return {
            "trend_data": trend_data # Bar or Line chart
        }

    def get_all_analytics(self) -> Dict[str, Any]:
        """Convenience method to return all metrics for the Client Dashboard."""
        if not self.rows:
            return {"error": "No data available for this client"}
            
        return {
            "loan_age": self.get_loan_age_analysis(),
            "average_loan_size": self.get_average_loan_size(),
            "lender_concentration": self.get_lender_concentration(),
            "trail_income": self.get_trail_income_analysis(),
            "run_off": self.get_run_off_analysis(),
            "book_size": self.get_book_size_trend(),
            "settlement_history": self.get_settlement_history()
        }
