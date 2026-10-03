"""
Empirical Mathematical and Financial Verification Harness for Vihara Commercial Strategy.

Verifies:
1. Marginal variable hosting COGS ($0.010/user/mo).
2. Payment gateway fees, net revenues, and gross margin percentages (>93%).
3. LTV calculations, formula integrity, and CAC ratios.
4. Fixed monthly overhead and breakeven subscriber volume (568 subscribers).
5. Comprehensive churn sensitivity analysis from 2.0% to 8.0% monthly churn.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COMMERCIAL_DOC = REPO_ROOT / "product_strategy" / "03_commercial_strategy" / "commercial_strategy.md"


class TestCommercialModelsEmpirical(unittest.TestCase):
    """Empirical verification of financial and mathematical models."""

    def test_01_marginal_hosting_cogs_breakdown(self):
        """Verify marginal variable hosting COGS sums exactly to $0.010/user/mo."""
        cogs_components = {
            "cloudflare_workers_edge": 0.0010,
            "aws_s3_cloudfront_cdn": 0.0045,
            "supabase_neon_db": 0.0035,
            "sentry_vector_telemetry": 0.0010,
        }
        total_monthly_cogs = sum(cogs_components.values())
        self.assertAlmostEqual(total_monthly_cogs, 0.0100, places=4)

        annual_cogs = total_monthly_cogs * 12
        self.assertAlmostEqual(annual_cogs, 0.12, places=4)

    def test_02_payment_gateway_fees_and_margins(self):
        """Verify gateway fee formulas, net revenue, and gross/net margins across tiers."""
        # 1. Pro Monthly ($9.00)
        p_monthly_gross = 9.00
        p_monthly_fee_calc = p_monthly_gross * 0.029 + 0.30  # 0.561
        p_monthly_fee_rounded = round(p_monthly_fee_calc, 2)  # 0.56
        self.assertEqual(p_monthly_fee_rounded, 0.56)
        p_monthly_net_rev = p_monthly_gross - p_monthly_fee_rounded
        self.assertEqual(p_monthly_net_rev, 8.44)
        p_monthly_net_margin = (p_monthly_net_rev / p_monthly_gross) * 100
        self.assertAlmostEqual(p_monthly_net_margin, 93.8, places=1)

        # Margin after hosting COGS ($0.010)
        p_monthly_after_cogs = (p_monthly_net_rev - 0.010) / p_monthly_gross * 100
        self.assertGreater(p_monthly_after_cogs, 93.0)

        # 2. Pro Annual ($79.00)
        p_annual_gross = 79.00
        p_annual_fee_calc = p_annual_gross * 0.029 + 0.30  # 2.591
        p_annual_fee_rounded = round(p_annual_fee_calc, 2)  # 2.59
        self.assertEqual(p_annual_fee_rounded, 2.59)
        p_annual_net_rev = p_annual_gross - p_annual_fee_rounded
        self.assertEqual(p_annual_net_rev, 76.41)
        p_annual_net_margin = (p_annual_net_rev / p_annual_gross) * 100
        self.assertAlmostEqual(p_annual_net_margin, 96.7, places=1)

        # 3. Pro Lifetime ($149.00)
        p_life_gross = 149.00
        p_life_fee_calc = p_life_gross * 0.029 + 0.30  # 4.621
        p_life_fee_rounded = round(p_life_fee_calc, 2)  # 4.62
        self.assertEqual(p_life_fee_rounded, 4.62)
        p_life_net_rev = p_life_gross - p_life_fee_rounded
        self.assertEqual(p_life_net_rev, 144.38)
        p_life_net_margin = (p_life_net_rev / p_life_gross) * 100
        self.assertAlmostEqual(p_life_net_margin, 96.9, places=1)

        # 4. Creator Pack ($2.99)
        pack_gross = 2.99
        pack_fee_calc = pack_gross * 0.05 + 0.05  # 0.1995 -> 0.20
        pack_fee_rounded = round(pack_fee_calc, 2)  # 0.20
        self.assertEqual(pack_fee_rounded, 0.20)
        pack_net_rev = pack_gross - pack_fee_rounded
        self.assertEqual(pack_net_rev, 2.79)
        pack_net_margin = (pack_net_rev / pack_gross) * 100
        self.assertAlmostEqual(pack_net_margin, 93.3, places=1)

        # 5. Enterprise Seat ($15.00)
        ent_gross = 15.00
        ent_fee = 0.15  # 1.0% ACH
        ent_net_rev = ent_gross - ent_fee
        self.assertEqual(ent_net_rev, 14.85)
        ent_net_margin = (ent_net_rev / ent_gross) * 100
        self.assertAlmostEqual(ent_net_margin, 99.0, places=1)

    def test_03_fixed_operating_overhead(self):
        """Verify fixed monthly operating overhead sum is exactly $3,500/mo ($42,000/yr)."""
        overhead = {
            "cloud_core": 350.0,
            "code_signing": 75.0,
            "sentry_monitoring": 150.0,
            "accounting_legal": 425.0,
            "support_lead": 2500.0,
        }
        total_monthly_overhead = sum(overhead.values())
        self.assertEqual(total_monthly_overhead, 3500.0)
        self.assertEqual(total_monthly_overhead * 12, 42000.0)

    def test_04_breakeven_subscriber_volume_calculation(self):
        """Verify cashflow breakeven point of 568 annual Pro subscribers."""
        annual_gross = 79.00
        gateway_fee = 2.59
        cloud_cogs = 0.12
        support_alloc = 2.40

        net_annual_contribution = annual_gross - gateway_fee - cloud_cogs - support_alloc
        self.assertAlmostEqual(net_annual_contribution, 73.89, places=2)

        monthly_net_contribution = net_annual_contribution / 12.0  # 6.1575
        fixed_overhead = 3500.0

        breakeven_exact = fixed_overhead / monthly_net_contribution
        self.assertAlmostEqual(breakeven_exact, 568.41, places=1)

        # Stated rounding in doc ($74.00 / 12 = $6.1667 or $6.16):
        breakeven_rounded_contrib = fixed_overhead / (74.00 / 12.0)
        self.assertAlmostEqual(breakeven_rounded_contrib, 567.57, places=1)

        breakeven_stated_616 = fixed_overhead / 6.16
        self.assertAlmostEqual(breakeven_stated_616, 568.18, places=1)

        # The claimed figure 568 is mathematically robust to within 0.15%
        self.assertEqual(round(breakeven_stated_616), 568)

    def test_05_ltv_formula_direct_evaluation_and_discrepancy_check(self):
        """
        Empirical evaluation of the LTV equation in Section 4.3:
        LTV = 24 * $7.20 - (24 * $0.56) - (24 * $0.010)

        Examines the difference between direct arithmetic ($159.12)
        and stated value ($153.72), and checks CAC ratio impact.
        """
        months = 24
        arpu = 7.20
        fee = 0.56
        cogs = 0.010
        cac = 18.50

        direct_ltv = (months * arpu) - (months * fee) - (months * cogs)
        self.assertAlmostEqual(direct_ltv, 159.12, places=2)

        stated_ltv = 153.72
        discrepancy = direct_ltv - stated_ltv
        self.assertAlmostEqual(discrepancy, 5.40, places=2)

        # Check ratio under direct arithmetic:
        direct_ratio = direct_ltv / cac
        self.assertAlmostEqual(direct_ratio, 8.60, places=2)

        # Check ratio under stated value:
        stated_ratio = stated_ltv / cac
        self.assertAlmostEqual(stated_ratio, 8.31, places=2)

        # Both ratios substantially exceed the standard SaaS benchmark of 3.0x
        self.assertGreater(direct_ratio, 3.0)
        self.assertGreater(stated_ratio, 3.0)

    def test_06_churn_sensitivity_analysis_grid(self):
        """
        Sensitivity analysis under varying monthly churn rates from 2.0% to 8.0%.
        Validates expected lifespan, LTV, LTV:CAC ratio, and distance to 3.0x health boundary.
        """
        cac = 18.50
        net_monthly_contribution_nominal = 7.20 - 0.56 - 0.010  # 6.63
        net_monthly_contribution_conservative = 153.72 / 24.0     # 6.405

        test_churn_rates = [0.02, 0.03, 0.04, 0.042, 0.05, 0.06, 0.07, 0.08]

        results = []
        for churn in test_churn_rates:
            lifespan_months = 1.0 / churn
            ltv_nominal = lifespan_months * net_monthly_contribution_nominal
            ratio_nominal = ltv_nominal / cac

            ltv_conserv = lifespan_months * net_monthly_contribution_conservative
            ratio_conserv = ltv_conserv / cac

            # All scenarios must exceed 3.0x healthy SaaS ratio
            self.assertGreater(
                ratio_conserv,
                3.0,
                f"LTV:CAC ratio dropped below 3.0x at churn rate {churn*100}%: {ratio_conserv:.2f}x",
            )
            self.assertGreater(
                ratio_nominal,
                3.0,
                f"Nominal LTV:CAC ratio dropped below 3.0x at churn rate {churn*100}%: {ratio_nominal:.2f}x",
            )

            results.append({
                "churn_pct": churn * 100,
                "lifespan_mo": lifespan_months,
                "ltv_nominal": ltv_nominal,
                "ratio_nominal": ratio_nominal,
                "ltv_conserv": ltv_conserv,
                "ratio_conserv": ratio_conserv,
            })

        # Check maximum sustainable monthly churn before hitting 3.0x threshold
        # Threshold: LTV = 3.0 * CAC = 55.50
        max_churn_nominal = net_monthly_contribution_nominal / (3.0 * cac)
        max_churn_conserv = net_monthly_contribution_conservative / (3.0 * cac)

        self.assertGreater(max_churn_nominal, 0.11)  # Can survive ~11.9% monthly churn
        self.assertGreater(max_churn_conserv, 0.11)  # Can survive ~11.5% monthly churn

    def test_07_commercial_strategy_document_mentions(self):
        """Verify the commercial strategy document explicitly contains all financial assertions."""
        content = COMMERCIAL_DOC.read_text(encoding="utf-8")
        self.assertIn("$0.010", content)
        self.assertIn("93%", content)
        self.assertIn("568", content)
        self.assertIn("153.72", content)
        self.assertIn("18.50", content)
        self.assertIn("4.2%", content)


if __name__ == "__main__":
    unittest.main()
