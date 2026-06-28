"""
Trend-Fit Engine — KOL Studio Phase 4: brand-safe trend matching.

Most tools just grab a trend and write something. This engine asks the real
question: *should THIS KOL ride this trend?* — judged against the persona's
DNA (topics, personality, tone, do/don'ts) so the personal brand isn't broken.

Returns, per trend: fit_score, verdict (fit | maybe | avoid), reason,
brand_risk, and a suggested on-brand angle if it fits.
"""

from __future__ import annotations

from typing import Any

from app.core.llm import generate_json


class TrendFitEngine:
    @staticmethod
    async def judge_trends(
        persona: Any,
        trends: list[dict[str, Any]],
        dna: Any | None = None,
    ) -> list[dict[str, Any]]:
        """Judge each trend's fit with the KOL's brand. Aligned to `trends`."""
        if not trends:
            return []

        if dna is not None:
            brand = f"""- Chủ đề thường viết: {', '.join(getattr(dna, 'topics', []) or []) or '—'}
- Tính cách: {', '.join(f"{m.get('trait')} {m.get('percent')}%" for m in (getattr(dna, 'personality_mix', []) or [])) or '—'}
- Giọng điệu: {getattr(dna, 'tone', '') or '—'}
- Văn phong: {getattr(dna, 'voice_summary', '') or '—'}
- Nên: {', '.join(getattr(dna, 'dos', []) or []) or '—'}
- Tránh: {', '.join(getattr(dna, 'donts', []) or []) or '—'}"""
        else:
            brand = f"""- Nghề: {getattr(persona, 'occupation', '')}
- Sở thích/ngách: {', '.join(getattr(persona, 'interests', []) or []) or '—'}
(Chưa có DNA — đánh giá dựa trên hồ sơ persona, độ chính xác thấp hơn.)"""

        trends_text = "\n".join(
            f"{i+1}. [{t.get('source','')}] {t.get('title','')}"
            f"{' — ' + t.get('description','') if t.get('description') else ''}"
            f" (độ hot: {round(float(t.get('popularity_score',0)))})"
            for i, t in enumerate(trends)
        )

        system_prompt = (
            "Bạn là cố vấn thương hiệu cá nhân cho KOL. Với mỗi trend, quyết định "
            "KOL CÓ NÊN đu trend này không, dựa trên việc nó có hợp ngách/giọng/giá "
            "trị thương hiệu của họ hay không. Bảo vệ thương hiệu — KHÔNG đu mọi "
            "trend. Nếu hợp, gợi ý góc tiếp cận đúng chất KOL. Trả về JSON."
        )
        user_prompt = f"""THƯƠNG HIỆU KOL: {persona.name}
{brand}

DANH SÁCH TREND:
{trends_text}

Với MỖI trend (theo thứ tự), đánh giá. Trả về JSON:
{{
  "results": [
    {{
      "index": 1,
      "fit_score": 0-100,
      "verdict": "fit | maybe | avoid",
      "reason": "vì sao hợp/không hợp (1-2 câu)",
      "brand_risk": "rủi ro với thương hiệu nếu đu (ngắn, hoặc 'thấp')",
      "angle": "nếu fit/maybe: góc tiếp cận đúng giọng KOL; nếu avoid: để trống"
    }}
  ]
}}
- Đúng {len(trends)} mục, theo thứ tự. verdict='avoid' nếu lệch tông/rủi ro cao.
- Viết tiếng Việt."""

        try:
            result = await generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.5,
                use_lite=False,
            )
        except Exception:
            result = {}

        judged = []
        if isinstance(result, dict):
            judged = result.get("results") or next(
                (v for v in result.values() if isinstance(v, list)), []
            )
        elif isinstance(result, list):
            judged = result

        out: list[dict[str, Any]] = []
        for i, t in enumerate(trends):
            j = judged[i] if i < len(judged) and isinstance(judged[i], dict) else {}
            verdict = (j.get("verdict") or "maybe").lower()
            if verdict not in ("fit", "maybe", "avoid"):
                verdict = "maybe"
            out.append({
                "trend": t,
                "fit_score": int(j.get("fit_score", 0) or 0),
                "verdict": verdict,
                "reason": (j.get("reason") or "").strip(),
                "brand_risk": (j.get("brand_risk") or "").strip(),
                "angle": (j.get("angle") or "").strip(),
            })
        out.sort(key=lambda x: x["fit_score"], reverse=True)
        return out
