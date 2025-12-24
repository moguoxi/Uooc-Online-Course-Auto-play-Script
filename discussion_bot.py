import time
import sys
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def run_discussion_bot():
    # ==========================================
    # ⚙️ 端口配置逻辑 (新增)
    # ==========================================
    # 检查是否有命令行参数传入端口号
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        current_port = int(sys.argv[1])
        mode_str = f"🚀 多开模式 (端口 {current_port})"
    else:
        current_port = 9222
        mode_str = f"👤 默认模式 (端口 {current_port})"

    print("===========================================")
    print(f"   优课在线 - 自动讨论工具 | {mode_str}")
    print("===========================================")

    # 输入逻辑保持不变 (每个窗口独立输入，方便发不同内容)
    target_title = input("请输入讨论标题: ").strip()
    target_content = input("请输入讨论内容: ").strip()
    repeat_times = 20
    # ⏱️ 间隔设置为 120 秒 (2分钟)
    interval_seconds = 120 

    if not target_title or not target_content:
        print("❌ 错误：标题或内容不能为空")
        return

    # 使用动态端口
    co = ChromiumOptions().set_local_port(current_port)
    try:
        page = ChromiumPage(co)
        tab = page.latest_tab
        print(f"✅ 已连接页面: {tab.title}")
    except Exception as e:
        print(f"❌ 浏览器连接失败: {e}")
        print(f"👉 请确认 Chrome 是否已在端口 {current_port} 启动")
        return

    for i in range(repeat_times):
        curr_num = i + 1
        print(f"\n[{time.strftime('%H:%M:%S')}] ⏳ 执行第 {curr_num}/{repeat_times} 次讨论...")
        
        start_time = time.time()
        success_this_round = False

        try:
            # 1. 点击“发起讨论”
            btn_start = tab.ele('xpath://span[contains(@ng-click, "layerAddDiscuss") and text()="发起讨论"]', timeout=5)
            if not btn_start:
                print("   ❌ 未找到“发起讨论”按钮，尝试刷新页面...")
                tab.refresh()
                time.sleep(3)
                continue
            
            btn_start.click()
            time.sleep(1.5) 

            # 2. 输入标题
            input_title = tab.ele('#disName', timeout=3)
            if input_title:
                input_title.clear()
                input_title.input(target_title)
            else:
                print("   ❌ 未找到标题框")
                continue

            # 3. 【写入】使用 JS 穿透 Iframe 输入内容
            safe_content = json.dumps(target_content)
            js_write = f"""
            (function() {{
                try {{
                    var holder = document.querySelector('.edui-editor-iframeholder');
                    var iframe = holder ? holder.querySelector('iframe') : null;
                    var doc = iframe ? (iframe.contentDocument || iframe.contentWindow.document) : null;
                    var body = doc ? doc.body : null;
                    
                    if (body) {{
                        body.innerHTML = {safe_content};
                        body.dispatchEvent(new Event('input', {{bubbles: true}}));
                        return "EXECUTED";
                    }}
                }} catch(e) {{ return "ERROR: " + e.message; }}
                return "NOT_FOUND";
            }})();
            """
            tab.run_js(js_write) 
            
            time.sleep(0.5)

            # 3.5 【读取】独立验证内容
            js_read = """
            (function() {
                try {
                    var holder = document.querySelector('.edui-editor-iframeholder');
                    var iframe = holder ? holder.querySelector('iframe') : null;
                    var doc = iframe ? (iframe.contentDocument || iframe.contentWindow.document) : null;
                    return doc ? (doc.body.innerText || doc.body.textContent) : "";
                } catch(e) { return ""; }
            })();
            """
            current_text = tab.run_js(js_read)
            
            is_content_ok = False
            if current_text and target_content in current_text:
                print(f"   ✍️ 内容校验通过: '{current_text.strip()[:10]}...'")
                is_content_ok = True
            elif current_text:
                print(f"   ⚠️ 内容校验不完全匹配 (读取到: '{current_text.strip()[:10]}...')，但继续尝试提交。")
                is_content_ok = True
            else:
                print("   ⚠️ 无法读取到内容，但根据反馈可能已输入，尝试强制提交...")
                is_content_ok = True 

            if not is_content_ok:
                continue

            # 4. 点击“确定”
            btn_confirm = tab.ele('xpath://button[contains(@ng-click, "addDiscuss") and contains(text(), "确定")]', timeout=3)
            if btn_confirm:
                btn_confirm.click()
                print("   ✅ 点击确定，发布成功。")
                success_this_round = True
                
                try:
                    tab.wait.ele_absent('xpath://button[contains(@ng-click, "addDiscuss")]', timeout=5)
                except:
                    pass 
            else:
                print("   ❌ 未找到确定按钮。")

        except Exception as e:
            print(f"   ⚠️ 本次循环异常: {e}")

        # 5. 等待逻辑
        if curr_num < repeat_times:
            elapsed = time.time() - start_time
            sleep_time = max(0, interval_seconds - elapsed)
            print(f"   😴 等待下一次（约 {int(sleep_time)} 秒后）...")
            time.sleep(sleep_time)

    print("\n🎉 任务全部完成！")

if __name__ == "__main__":
    run_discussion_bot()