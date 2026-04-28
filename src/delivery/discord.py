"""
delivery/discord.py — Discord webhook adapter.
"""

from __future__ import annotations

import requests
import datetime
from typing import Optional

from src.delivery.base import BasePlatformAdapter, DeliveryResult, PlatformConfig
from src.models import CuratedNewsletter


class DiscordAdapter(BasePlatformAdapter):
    """Gửi newsletter qua Discord webhook sử dụng Rich Embeds chuyên nghiệp."""
    platform_name = "discord"

    def connect(self) -> bool:
        return self.validate()

    def disconnect(self):
        pass

    def send_html(self, html_text: str, curated: Optional[CuratedNewsletter] = None, **kwargs) -> DeliveryResult:
        webhook_url = self.config.api_token
        if not webhook_url:
            return DeliveryResult(success=False, platform=self.platform_name, error="Missing Discord Webhook URL")

        # Nếu có curated, gửi bằng Embeds cực đẹp (Premium)
        if curated:
            return self._send_rich_embeds(curated, webhook_url)
        else:
            # Fallback nếu không có curated
            import re
            plain = re.sub(r"<[^>]+>", "", html_text).strip()
            chunks = [plain[i:i + 1900] for i in range(0, len(plain), 1900)]
            last_result = DeliveryResult(success=False, platform=self.platform_name)

            for chunk in chunks:
                try:
                    resp = requests.post(webhook_url, json={"content": chunk}, timeout=30)
                    resp.raise_for_status()
                    last_result = DeliveryResult(success=True, platform=self.platform_name)
                except Exception as e:
                    last_result = DeliveryResult(success=False, platform=self.platform_name, error=str(e))
            return last_result

    def _send_rich_embeds(self, curated: CuratedNewsletter, webhook_url: str) -> DeliveryResult:
        payloads = []
        
        # 1. Main Header Embed
        payloads.append({
            "embeds": [{
                "title": f"🗞️ {curated.headline}",
                "description": curated.lead,
                "color": 3447003, # Màu xanh Blue
                "footer": {"text": "AI News Agent • Daily Digest"},
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }]
        })
        
        # 2. GitHub Repos Embeds (Thiết kế dạng Card)
        for r in curated.repos:
            desc = f"**TL;DR:** {r.tldr}\n\n**💡 Góc nhìn Dev:** {r.why_it_matters}\n\n"
            if r.highlights:
                desc += "\n".join([f"• {h}" for h in r.highlights])
                
            fields = []
            if r.language:
                fields.append({"name": "Language", "value": r.language, "inline": True})
            if r.stars_today:
                fields.append({"name": "Stars Today", "value": f"⭐ {r.stars_today}", "inline": True})
            if r.rank:
                fields.append({"name": "Rank", "value": f"#{r.rank}", "inline": True})
                
            payloads.append({
                "embeds": [{
                    "title": f"🔥 {r.title}",
                    "url": r.url,
                    "description": desc,
                    "color": 15105570, # Màu cam (Orange)
                    "fields": fields
                }]
            })
            
        # 3. Articles Embeds (Tin Tức)
        for a in curated.articles:
            is_security = a.source_signal and "security" in a.source_signal.lower()
            color = 15158332 if is_security else 10181046 # Màu đỏ (Security), Màu Tím (AI)
            icon = "🛡️" if is_security else "🤖"
            source = a.source_label or ("Security News" if is_security else "Tech News")
            
            desc = f"**TL;DR:** {a.tldr}\n\n**💡 Tại sao quan trọng:** {a.why_it_matters}"
            payloads.append({
                "embeds": [{
                    "author": {"name": f"{icon} {source}"},
                    "title": a.title,
                    "url": a.url,
                    "description": desc,
                    "color": color
                }]
            })
            
        # Gửi từng phần payload vào webhook.
        # Lưu ý: Discord limit tối đa 10 embeds per message, nên ta loop gửi tuần tự cho an toàn.
        last_result = DeliveryResult(success=False, platform=self.platform_name)
        for p in payloads:
            try:
                resp = requests.post(webhook_url, json=p, timeout=30)
                resp.raise_for_status()
                last_result = DeliveryResult(success=True, platform=self.platform_name)
            except Exception as e:
                return DeliveryResult(success=False, platform=self.platform_name, error=str(e))
                
        return last_result
