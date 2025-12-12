# answer_logic.py
import time
import re
from DrissionPage import ChromiumPage, ChromiumOptions
from config import (
    CHROME_DEBUG_PORT, 
    DOM_WAIT, 
    DOM_CLICK_WAIT, 
    QUIZ_CHECK_RETRIES
)

class QuizSolver:
    def __init__(self):
        self.page = None
        self.tab = None
        
    def _ensure_connection(self):
        if self.tab: return
        print("🚀 正在连接浏览器...")
        co = ChromiumOptions().set_local_port(CHROME_DEBUG_PORT)
        try:
            self.page = ChromiumPage(co)
            self.tab = self.page.latest_tab
            print(f"✅ 已连接: {self.tab.title}")
        except Exception as e:
            print(f"❌ 连接失败: {e}")

    def get_quiz_layer(self):
        """
        【终极修复】仅获取被 .layui-layer 包裹的 #quizLayer
        """
        if not self.tab: self._ensure_connection()
        
        # 使用结构化选择器，直接忽略裸露的幽灵节点
        ele = self.tab.ele('css:div.layui-layer #quizLayer', timeout=0.1)
        
        if not ele: return None
        if ele.states.is_displayed: return ele
        return None

    def get_all_options(self):
        layer = self.get_quiz_layer()
        if not layer: return {}
        options_map = {}
        labels = layer.eles('css:label.ti-a')
        for label in labels:
            input_ele = label.ele('css:input')
            if input_ele:
                val = input_ele.attr('value')
                if val:
                    itype = input_ele.attr('type') or 'checkbox'
                    options_map[val.upper()] = {
                        'label': label, 
                        'input': input_ele,
                        'type': itype
                    }
        return options_map

    def get_selected_options(self, options_map):
        selected = []
        for val, info in options_map.items():
            input_ele = info['input']
            if input_ele.property('checked') is True:
                selected.append(val)
                continue
            class_attr = input_ele.attr('class') or ""
            if "ng-valid-parse" in class_attr:
                selected.append(val)
        return selected

    def adjust_selection(self, target_list):
        options_map = self.get_all_options()
        if not options_map: return False

        current_selected = self.get_selected_options(options_map)
        print(f"🧐 [状态检测] 目标:{target_list} | 当前已选:{current_selected}")
        
        if set(current_selected) == set(target_list):
            print("   ✅ 状态完美，无需调整")
            return True

        extra_options = [o for o in current_selected if o not in target_list]
        missing_options = [o for o in target_list if o not in current_selected]

        try:
            for opt in extra_options:
                info = options_map.get(opt)
                if info and info['type'] == 'radio': continue 
                print(f"   🧹 [清理] 尝试取消选项 {opt}...")
                if info:
                    info['label'].click()
                    time.sleep(DOM_CLICK_WAIT) 
                
            for opt in missing_options:
                print(f"   ✍️ [填补] 尝试选中选项 {opt}...")
                if opt in options_map:
                    options_map[opt]['label'].click()
                    time.sleep(DOM_CLICK_WAIT) 
        except:
            print("   ⚠️ 选项交互中断 (答题框可能已关闭)")
            return False
            
        time.sleep(DOM_WAIT)

        final_selected = self.get_selected_options(options_map)
        if set(final_selected) == set(target_list):
            print(f"   ✅ 调整完成，当前状态: {final_selected}")
            return True
        else:
            print(f"   ⚠️ 调整后状态仍不符: {final_selected}")
            return False

    def submit_and_check(self, target_answers=None):
        """
        点击确定，并检测状态
        """
        layer = self.get_quiz_layer()
        if not layer: return "GONE" 
        
        submit_btn = layer.ele('xpath://button[contains(text(), "确定")]')
        if submit_btn:
            print("⚡ 点击 [确定]...")
            submit_btn.click()
            time.sleep(DOM_WAIT)
        else:
            print("❌ 未找到确定按钮")
            return "ERROR"
            
        print("🔍 校验结果...", end="")
        for _ in range(QUIZ_CHECK_RETRIES): 
            # 1. 检查答题框是否存在
            if not self.get_quiz_layer():
                print("\n🎉 答题框消失，提交成功！")
                return "GONE"

            # 2. 检查是否有错误提示
            try:
                layer = self.get_quiz_layer()
                if not layer: return "GONE"
                
                hint_ele = layer.ele('xpath:.//*[contains(text(), "正确答案")]', timeout=0.1)
                if hint_ele and hint_ele.states.is_displayed:
                    text = hint_ele.text
                    correct_answers = re.findall(r'["\']([A-Z])["\']', text)
                    
                    if target_answers and set(correct_answers) == set(target_answers):
                        print(f"\n🎉 答案 {correct_answers} 正确！(强制判定成功)")
                        return "GONE" 
                    
                    print(f"\n💡 获取到正确答案: {correct_answers}")
                    return correct_answers 
            except:
                pass
            
            time.sleep(DOM_WAIT)
            print(".", end="")
            
        print("\n⏳ 校验超时 (未消失且无新提示)。")
        return "TIMEOUT"

    def run(self):
        self._ensure_connection()
        print("\n--- 开始答题流程 ---")
        
        # 1. 阶段一：盲选 A
        print("\n>>> [阶段一] 尝试盲选 A")
        self.adjust_selection(['A'])
        
        result = self.submit_and_check(target_answers=['A'])
        
        if result == "GONE": return 
        if result == "ERROR": return
            
        # 2. 阶段二：根据答案修正
        if isinstance(result, list):
            correct_answers = result
            print(f"\n>>> [阶段二] 使用正确答案重试: {correct_answers}")
            
            self.adjust_selection(correct_answers)
            
            final_res = self.submit_and_check(target_answers=correct_answers)
            
            if final_res == "GONE":
                print("🎉 流程结束。")
            else:
                print("✅ 流程结束。")

if __name__ == "__main__":
    solver = QuizSolver()
    solver.run()