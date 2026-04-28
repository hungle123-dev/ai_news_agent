"""
delivery/email.py — Email adapter qua SMTP.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import html

from src.delivery.base import BasePlatformAdapter, DeliveryResult, PlatformConfig
from src.models import CuratedNewsletter

_TEMPLATE_PATH = Path(__file__).parents[1] / "templates" / "email_template.html"


@dataclass
class EmailConfig(PlatformConfig):
    """Config mở rộng cho Email."""
    smtp_host: str = ""
    smtp_port: int = 587
    password: str = ""
    from_email: str = ""
    to_email: str = ""


class EmailAdapter(BasePlatformAdapter):
    """Gửi newsletter qua SMTP Email."""
    platform_name = "email"

    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.email_config: EmailConfig = config

    def connect(self) -> bool:
        return self.validate()

    def disconnect(self):
        pass

    def send_html(self, html_text: str, subject: str = "AI News", curated: CuratedNewsletter | None = None, **kwargs) -> DeliveryResult:
        cfg = self.email_config
        
        # Nếu được truyền object CuratedNewsletter, ta tự động render HTML xịn
        if curated is not None and _TEMPLATE_PATH.exists():
            final_html = self._render_beautiful_email(curated)
        else:
            final_html = html_text

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = cfg.from_email or cfg.api_token or ""
            msg["To"] = cfg.to_email

            msg.attach(MIMEText(final_html, "html", "utf-8"))

            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(cfg.api_token or "", cfg.password)
                server.sendmail(msg["From"], [msg["To"]], msg.as_string())

            return DeliveryResult(success=True, platform=self.platform_name)
        except Exception as e:
            return DeliveryResult(success=False, platform=self.platform_name, error=str(e))

    def _render_beautiful_email(self, curated: CuratedNewsletter) -> str:
        """Bơm dữ liệu vào template HTML Email."""
        template = _TEMPLATE_PATH.read_text(encoding="utf-8")
        
        from datetime import datetime
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'vi_VN.UTF-8')
        except Exception:
            pass
        date_str = datetime.now().strftime("%A, %d/%m/%Y")
        total_items = len(curated.repos) + len(curated.articles)
        
        # Render danh sách Repos
        repos_html = []
        for r in curated.repos:
            # badges
            badges = []
            if r.language:
                badges.append(f'<span class="badge badge-lang">{html.escape(r.language)}</span>')
            if r.stars_today:
                badges.append(f'<span class="badge badge-stars">⭐ {r.stars_today:,} hôm nay</span>')
            if r.rank:
                badges.append(f'<span class="badge badge-rank">🆕 Trending #{r.rank}</span>')
            badges_str = "".join(badges)
            
            h_list = "".join([f"<li>{html.escape(h)}</li>" for h in r.highlights])
            highlights = f'<ul class="highlights-list">{h_list}</ul>' if h_list else ""
            
            repo_block = f"""
            <div class="repo-card">
              <div class="repo-card-top">
                <div>
                  <div class="repo-meta">
                    {badges_str}
                  </div>
                  <div class="repo-title">
                    <a href="{r.url}" target="_blank">{html.escape(r.title)}</a>
                  </div>
                </div>
              </div>
              <p class="repo-tldr">{html.escape(r.tldr)}</p>
              <div class="repo-insight">
                <strong>💡 Góc nhìn Dev:</strong> {html.escape(r.why_it_matters)}
              </div>
              {highlights}
              <a href="{r.url}" class="btn-repo" target="_blank">Xem Repository →</a>
            </div>
            """
            repos_html.append(repo_block)

        # Render danh sách Articles
        ai_articles_html = []
        security_articles_html = []
        for a in curated.articles:
            is_security = a.source_signal and "security" in a.source_signal.lower()
            dot_class = "dot-security" if is_security else "dot-anthropic"
            source_name = a.source_label or ("Security News" if is_security else "Tech News")
            
            article_block = f"""
            <div class="article-item">
              <div class="source-row">
                <div class="source-dot {dot_class}"></div>
                <span class="source-name">{html.escape(source_name)}</span>
              </div>
              <div class="article-title">
                <a href="{a.url}" target="_blank">{html.escape(a.title)}</a>
              </div>
              <p class="article-tldr">{html.escape(a.tldr)}</p>
              <p class="article-why">
                <strong>Tại sao quan trọng:</strong> {html.escape(a.why_it_matters)}
              </p>
            </div>
            """
            if is_security:
                security_articles_html.append(article_block)
            else:
                ai_articles_html.append(article_block)

        # Trộn tất cả vào template
        final = template.replace("{date}", date_str)
        final = final.replace("{total_items}", str(total_items))
        final = final.replace("{headline}", html.escape(curated.headline))
        final = final.replace("{lead}", html.escape(curated.lead))
        
        final = final.replace("{repos_html}", "".join(repos_html) or "<div style='padding:0 40px 32px;'><p class='article-tldr'>Không có repo nổi bật hôm nay.</p></div>")
        final = final.replace("{ai_articles_html}", "".join(ai_articles_html) or "<div style='padding:0 40px 32px;'><p class='article-tldr'>Không có tin AI nổi bật.</p></div>")
        
        # Ẩn cả section Security nếu không có tin
        if security_articles_html:
            final = final.replace("{security_articles_html}", "".join(security_articles_html))
        else:
            final = final.replace(
                """<!-- SECURITY NEWS -->
  <div style="padding-top: 32px; padding-bottom: 8px;">
    <div class="section-label" style="padding: 0 40px;">
      <span style="font-size:18px;">🛡️</span>
      <span class="text" style="color: #EF4444;">Bảo mật</span>
      <div class="line"></div>
    </div>
    {security_articles_html}
  </div>""", 
                ""
            )
            final = final.replace("{security_articles_html}", "")

        # Tạm thời ẩn section Quick bites vì agent hiện tại chưa gen ra mục này
        final = final.replace(
            """<!-- QUICK BITES -->
  {quickbites_html}""", 
            ""
        )
        final = final.replace("{quickbites_html}", "")
        
        return final
