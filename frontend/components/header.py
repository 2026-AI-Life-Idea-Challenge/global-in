"""
frontend/components/header.py
글로벌 헤더
"""
import streamlit as st
import streamlit.components.v1 as components


def render_header(right_label: str = "", show_nav: bool = False):
    col_logo, col_right = st.columns([5, 2])

    with col_logo:
        # 홈 이동용 버튼 (JS가 숨기고 텍스트 div로 교체)
        if st.button("⊙  Global-In .", key="logo_home_btn"):
            st.session_state["page"] = "home"
            st.rerun()

    with col_right:
        st.markdown(
            f'<div style="text-align:right;font-size:0.85rem;color:#666;padding:0.6rem 0;">● {right_label}</div>',
            unsafe_allow_html=True,
        )

    # JS: 버튼을 완전히 숨기고, 순수 텍스트 div 삽입
    components.html(
        """
        <script>
        (function () {
            var FAKE_ID = 'gi-logo-fake';

            function setup() {
                try {
                    var doc = window.parent.document;
                    if (doc.getElementById(FAKE_ID)) return;

                    var targetBtn = null;
                    doc.querySelectorAll('button').forEach(function (b) {
                        if (b.textContent.indexOf('Global-In') !== -1) {
                            targetBtn = b;
                        }
                    });
                    if (!targetBtn) return;

                    var wrapper = targetBtn.closest('[data-testid="stButton"]') || targetBtn.parentNode;

                    var fake = doc.createElement('div');
                    fake.id = FAKE_ID;
                    fake.textContent = '⊙ Global-In .';
                    fake.style.cssText = [
                        'font-size:1.9rem',
                        'font-weight:900',
                        'color:#1a1a1a',
                        'cursor:pointer',
                        'letter-spacing:-0.01em',
                        'line-height:1.3',
                        'padding:2px 0 2px 2px',
                        'margin-left:-2px',
                        'display:block',
                        'overflow:visible',
                        'user-select:none',
                        '-webkit-user-select:none',
                    ].join(';');

                    fake.addEventListener('click', function () {
                        targetBtn.click();
                    });

                    // 부모 컨테이너들 overflow:visible 처리
                    var el = wrapper;
                    for (var i = 0; i < 6; i++) {
                        if (!el || !el.parentNode) break;
                        el.style.overflow = 'visible';
                        el = el.parentNode;
                    }

                    wrapper.style.display = 'none';
                    wrapper.parentNode.insertBefore(fake, wrapper);

                } catch (e) {
                    console.error('[gi-logo]', e);
                }
            }

            [50, 150, 400, 900, 2000].forEach(function (ms) {
                setTimeout(setup, ms);
            });

            try {
                var obs = new MutationObserver(function () {
                    if (!window.parent.document.getElementById(FAKE_ID)) {
                        setup();
                    }
                });
                obs.observe(window.parent.document.body, {
                    childList: true,
                    subtree: true,
                });
            } catch (e) {}
        })();
        </script>
        """,
        height=0,
    )

    st.markdown(
        "<hr style='margin:0 0 1rem;border:none;border-top:1px solid #e8e8e8;'>",
        unsafe_allow_html=True,
    )
