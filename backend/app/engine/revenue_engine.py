"""
Revenue Engine — KOL Studio Phase 5: revenue-goal-driven content planning.

The question customers pay for: "muốn +20% doanh thu affiliate tháng này thì
nên đăng gì?". This engine:
1. Computes the math deterministically from real tracking data (commission per
   conversion, conversion rate) — with honest assumptions where data is missing.
2. Asks the LLM for a brand-safe, non-spam content plan that drives that goal:
   which product to focus, how to weave it into value content, post ideas.
"""

from __future__ import annotations

import math
from typing import Any

from app.core.llm import generate_json


def compute_math(current: dict[str, Any], target_revenue: float) -> dict[str, Any]:
    """Deterministic revenue math. Honest about what it can/can't estimate."""
    R = float(current.get("total_revenue", 0) or 0)
    C = int(current.get("total_conversions", 0) or 0)
    K = int(current.get("total_clicks", 0) or 0)

    avg_comm = round(R / C, 0) if C else None        # commission per conversion
    cr = round(C / K * 100, 2) if K else None         # conversion rate %
    gap = max(0.0, round(target_revenue - R, 0))

    assumptions: list[str] = []
    est_conv = None
    est_clicks = None

    if gap <= 0:
        assumptions.append("Đã đạt/vượt mục tiêu — tập trung giữ nhịp & nhân bản bài ra tiền.")
    elif avg_comm:
        est_conv = math.ceil(gap / avg_comm)
        assumptions.append(f"Hoa hồng TB/đơn ≈ {int(avg_comm):,}đ (từ {C} đơn lịch sử).")
        if cr:
            est_clicks = math.ceil(est_conv / (cr / 100))
            assumptions.append(f"Tỷ lệ chuyển đổi ≈ {cr}% → cần ~{est_clicks:,} click.")
        else:
            assumptions.append("Chưa có dữ liệu click → không ước tính được số click cần.")
    else:
        assumptions.append(
            "Chưa có đơn hàng nào → không ước tính được từ lịch sử. "
            "Hãy ghi nhận vài đơn (tab Kiếm tiền) để AI tính chính xác hơn."
        )

    return {
        "current_revenue": R,
        "target_revenue": round(target_revenue, 0),
        "gap": gap,
        "avg_commission_per_conversion": avg_comm,
        "conversion_rate": cr,
        "est_conversions_needed": est_conv,
        "est_clicks_needed": est_clicks,
        "assumptions": assumptions,
    }


class RevenueEngine:
    @staticmethod
    async def plan(
        persona: Any,
        current: dict[str, Any],
        products: list[dict[str, Any]],
        math_block: dict[str, Any],
        days: int = 30,
        dna: Any | None = None,
        insights: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """LLM builds the revenue-driven content plan (focus + post ideas)."""
        prod_text = "\n".join(
            f"- {p['name']} (danh mục {p.get('category','')}, HH {p.get('commission_rate',0)}%, "
            f"đã bán {p.get('total_conversions',0)}, doanh thu {int(p.get('total_revenue',0) or 0):,}đ)"
            for p in products
        ) or "(chưa có sản phẩm — gợi ý chung)"

        dna_block = ""
        if dna is not None:
            dna_block = (
                f"Văn phong: {getattr(dna,'voice_summary','') or '—'}; "
                f"Chủ đề: {', '.join(getattr(dna,'topics',[]) or []) or '—'}"
            )
        best_times = (insights or {}).get("best_times", [])

        system_prompt = (
            "Bạn là cố vấn tăng trưởng doanh thu cho KOL affiliate. Lập kế hoạch "
            "nội dung HƯỚNG DOANH THU nhưng KHÔNG spam: chủ yếu tạo giá trị, lồng "
            "sản phẩm tự nhiên vào đúng chỗ (funnel ~70 giá trị / 20 câu chuyện / "
            "10 bán hàng). Ưu tiên sản phẩm hoa hồng cao & hợp ngách. Trả về JSON."
        )
        user_prompt = f"""KOL: {persona.name} — {getattr(persona,'occupation','')}
{dna_block}
Khung thời gian: {days} ngày. Khung giờ tốt: {', '.join(best_times) or '—'}

HIỆN TRẠNG: doanh thu {int(current.get('total_revenue',0) or 0):,}đ, {current.get('total_conversions',0)} đơn, CR {math_block.get('conversion_rate') or '—'}%
MỤC TIÊU: {int(math_block['target_revenue']):,}đ (còn thiếu {int(math_block['gap']):,}đ)
{('Ước tính cần ~' + str(math_block['est_conversions_needed']) + ' đơn nữa.') if math_block.get('est_conversions_needed') else ''}

SẢN PHẨM:
{prod_text}

Lập kế hoạch. Trả về JSON:
{{
  "strategy": "tóm tắt chiến lược 2-3 câu để đạt mục tiêu",
  "focus_products": [{{"name": "sp nên đẩy", "why": "vì sao (HH cao/hợp ngách/đang bán tốt)"}}],
  "plan": [
    {{"pillar": "knowledge|story|sales", "product": "tên sp lồng vào (hoặc trống)", "angle": "góc nội dung", "hook": "câu mở đầu", "expected": "vai trò trong phễu (vd: hâm nóng / chốt đơn)"}}
  ],
  "warnings": ["lưu ý tránh spam / rủi ro (nếu có)"]
}}
- plan khoảng 8 mục, đa dạng, đúng tỷ lệ funnel, bài sales lồng sản phẩm thật.
- Viết tiếng Việt."""

        try:
            result = await generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                use_lite=False,
            )
        except Exception:
            result = {}
        if not isinstance(result, dict):
            result = {}
        result.setdefault("strategy", "")
        result.setdefault("focus_products", [])
        result.setdefault("plan", [])
        result.setdefault("warnings", [])
        return result
