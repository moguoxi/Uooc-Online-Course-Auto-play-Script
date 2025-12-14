# quiz_logic.py (文字提取版)
import time
import datetime
import json # 引入 json 库以便输出结构化的数据
from DrissionPage import ChromiumPage, ChromiumOptions

class QuizSolver:
    def __init__(self, page):
        self.page = page
        self.known_answers = {} 
        self.current_guess_index = 0 
        self.options_list = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'] 
        self.context = None 

    def _get_context(self):
        """寻找题目上下文 (自动识别 Iframe 或主页面)"""
        # 核心特征：页面或iframe中包含 queContainer 类
        xpath_selector = 'xpath://div[contains(@class, "queContainer")]'
        
        # 1. 检查主文档
        if self.page.ele(xpath_selector): return self.page
        
        # 2. 检查 iframe
        try:
            frames = self.page.eles('tag:iframe')
            for frame in frames:
                try:
                    if frame.ele(xpath_selector): return frame
                except: pass
        except: pass
        return None

    def is_quiz_page(self):
        """
        供外部(main.py)调用，判断当前页是否为测验页
        """
        return self._get_context() is not None

    def run(self):
        """
        执行测验数据提取流程
        """
        print("📝 [提取] 检测到测验，初始化数据提取引擎...")
        self.context = self._get_context()
        
        if not self.context:
            print("❌ 未能找到题目容器，无法提取数据。")
            return
            
        quiz_data = self._extract_quiz_data()
        
        if not quiz_data:
            print("❌ 提取到空数据。")
            return

        # ==========================================
        # 🎯 最终输出 (用于喂给 AI)
        # ==========================================
        print("\n" + "="*50)
        print("✨ 测验数据提取完成 (AI 预处理格式) ✨")
        print("="*50)

        formatted_output = []
        for idx, q in enumerate(quiz_data):
            
            # 1. 构造选项字符串
            options_str = []
            for opt in q['options']:
                options_str.append(f"{opt['key']}. {opt['text']}")
            
            # 2. 构造单题输出
            output = f"--- 题目 {idx + 1} ---\n"
            output += f"类型: {q['type']}\n"
            output += f"题干: {q['question_text']}\n"
            output += "选项:\n"
            output += "\n".join([f"    {s}" for s in options_str])
            
            formatted_output.append(output)
            
        print("\n\n".join(formatted_output))
        
        print("\n" + "="*50)
        
        # 如果需要 JSON 格式，可以额外输出
        # print("\n--- 原始 JSON 格式 ---\n")
        # print(json.dumps(quiz_data, indent=4, ensure_ascii=False))


    def _extract_quiz_data(self):
        """
        核心提取逻辑：遍历所有题目容器，提取题型、题干和选项。
        """
        if not self.context: return []
        
        que_containers = self.context.eles('xpath://div[contains(@class, "queContainer")]')
        if not que_containers: 
            print("❌ 提取器：未找到任何题目容器。")
            return []
            
        extracted_data = []
        
        for index, container in enumerate(que_containers):
            question_data = {
                'id': index + 1,
                'type': '未知',
                'question_text': 'N/A',
                'options': []
            }
            
            try:
                # --- 1. 提取题干 ---
                # HTML 结构: <div class="ti-q-c">...</div>
                question_text_ele = container.ele('css:.ti-q-c', timeout=0.1)
                if question_text_ele:
                    # 清理HTML标签，只保留纯文本
                    question_data['question_text'] = question_text_ele.text.strip().replace('\n', ' ')

                # --- 2. 遍历选项 ---
                # HTML 结构: <label class="ti-a"> <span class="ti-a-i">A.</span> <div class="ti-a-c">...</div> </label>
                options = container.eles('css:label.ti-a')
                
                # 确定题型（以第一个找到的 input 为准）
                q_type = '未知'
                first_input = container.ele('css:input[type="radio"], input[type="checkbox"]', timeout=0.1)
                if first_input:
                    q_type = '单选题' if first_input.attr('type') == 'radio' else '多选题'
                question_data['type'] = q_type
                
                
                for label in options:
                    option_key = '?'
                    option_text = 'N/A'
                    
                    # 提取选项字母 (Key)
                    letter_span = label.ele('css:.ti-a-i', timeout=0.1)
                    if letter_span:
                        option_key = letter_span.text.replace('.', '').strip().upper()
                        
                    # 提取选项文本 (Text)
                    text_div = label.ele('css:.ti-a-c', timeout=0.1)
                    if text_div:
                        option_text = text_div.text.strip().replace('\n', ' ')
                    
                    if option_key != '?':
                        question_data['options'].append({
                            'key': option_key,
                            'text': option_text
                        })
                        
                extracted_data.append(question_data)
                
            except Exception as e:
                print(f"⚠️ 提取题目 {index + 1} 时出错: {e}")
                
        return extracted_data

# --- 以下不再需要的旧方法全部删除或留空 ---

    def _log_question_status(self, que_containers):
        pass # 移除

    def fill_answers(self):
        pass # 移除
        
    def _safe_click(self, inp):
        pass # 移除

    def submit_paper(self):
        pass # 移除

    def check_success_dialog(self):
        pass # 移除

    def analyze_results(self):
        pass # 移除

# ==========================================
# 🐛 独立调试入口
# ==========================================
if __name__ == "__main__":
    print("===========================================")
    print("   测验逻辑独立调试工具 (文字提取模式)")
    print("===========================================")
    print("👉 请确保浏览器已打开，且当前标签页是【测验页面】")
    
    # 1. 连接浏览器
    co = ChromiumOptions().set_local_port(9222)
    try:
        page = ChromiumPage(co)
        tab = page.latest_tab
        print(f"✅ 已连接页面: {tab.title}")
        print("🚀 3秒后开始运行提取逻辑...")
        time.sleep(3)
        
        # 2. 初始化并运行
        solver = QuizSolver(tab)
        
        # 简单检查环境
        if not solver.is_quiz_page():
            print("⚠️ 警告: 当前页面似乎没有检测到题目容器 (queContainer)。")
            print("   -> 请手动切换到测验页面，或检查页面加载是否完成。")
        
        solver.run()
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n程序结束。")