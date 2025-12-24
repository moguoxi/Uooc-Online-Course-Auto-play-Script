# navigator_logic.py
import re
from DrissionPage import ChromiumPage, ChromiumOptions

# ==========================================
# 🛠️ 虚拟节点类 (内存运算)
# ==========================================
class VirtualItem:
    def __init__(self, element, index_path, current_url, parent=None): 
        self.element = element 
        self.index_path = index_path
        self.parent = parent 
        
        # 1. 获取基础属性
        self.class_attr = element.attr('class') or ""
        
        # 2. 解析标题部分
        if 'basic' in self.class_attr:
            self.title_div = element
        else:
            self.title_div = element.ele('xpath:./div[contains(@class, "basic")]', timeout=0.01)
        
        if self.title_div:
            self.text = self.title_div.text.replace('\n', ' ').strip()
            self.href = self.title_div.attr('href') or ""
            self.title_class = self.title_div.attr('class') or ""
        else:
            self.text = "Unknown"
            self.href = ""
            self.title_class = ""
            
        # 3. 状态属性
        self.is_completed = "complete" in self.title_class and "uncomplete" not in self.title_class
        self.is_active = "active" in self.title_class
        self.is_unopen = "unopen" in self.class_attr
        
        # 4. 锚点判定 (Active/ID/语义)
        self.is_self_active = False
        if self.is_active:
            self.is_self_active = True
        else:
            ids = re.findall(r'(\d+)', self.href)
            node_id = ids[-1] if ids else None
            if node_id and len(node_id) > 4 and node_id in current_url:
                self.is_self_active = True
            elif '/files' in current_url or '/quiz' in current_url:
                semantic_map = {'/files': ['附件', '文档'], '/quiz': ['测验', '测试', '作业', '考试']}
                for url_key, keys in semantic_map.items():
                    if url_key in current_url and any(k in self.text for k in keys):
                        self.is_self_active = True
                        break

        # 5. 结构判定
        if element.tag == 'li':
            self.child_res = element.eles('xpath:./div[contains(@class, "resourcelist")]/div[contains(@class, "basic")]', timeout=0.01)
            self.child_ul = element.eles('xpath:./ul/li', timeout=0.01)
        else:
            self.child_res = []
            self.child_ul = []
            
        has_arrow = bool(self.title_div.ele('css:.icon-xiangxia, .icon-xiangshang', timeout=0.01)) if self.title_div else False
        
        self.is_container = bool(self.child_res or self.child_ul or has_arrow)
        self.is_collapsed = self.is_container and (self.is_unopen or (not self.child_res and not self.child_ul))
        
        # 6. 视频判定
        self.is_video = False
        if not self.is_container and self.title_div:
            has_icon = bool(self.title_div.ele('css:.icon-video', timeout=0.01))
            has_text = "视频" in self.text
            self.is_video = has_icon or has_text

        # 7. 【核心修改】 非视频任务判定 (跳过列表)
        # 凡是包含这些关键词的节点，无论是否完成，都视为"应跳过"
        self.should_skip = False
        if not self.is_container and self.title_div:
            # 加入 "附件", "文档", "PPT", "链接" 等非视频内容
            skip_keywords = ['测验', '测试', '作业', '考试', '附件', '文档', '课前', '复习', '链接', 'PPT']
            if any(k in self.text for k in skip_keywords):
                self.should_skip = True

# ==========================================
# 🌳 内存树构建与遍历
# ==========================================
def build_tree_and_find_anchor(page, root_lis, current_url):
    virtual_roots = []
    active_path = None
    
    def _recursive_build(element, current_path, parent_node): 
        nonlocal active_path
        node = VirtualItem(element, current_path, current_url, parent=parent_node) 
        
        if node.is_self_active:
            active_path = current_path
            
        node.children = []
        child_counter = 0
        
        for res_div in node.child_res:
            child_counter += 1
            child_path = current_path + [child_counter]
            child_node = _recursive_build(res_div, child_path, node) 
            node.children.append(child_node)
            
        for ul_li in node.child_ul:
            child_counter += 1
            child_path = current_path + [child_counter]
            child_node = _recursive_build(ul_li, child_path, node) 
            node.children.append(child_node)
            
        return node

    for i, li in enumerate(root_lis):
        path = [i + 1]
        v_node = _recursive_build(li, path, None) 
        virtual_roots.append(v_node)
        
    return virtual_roots, active_path

# ==========================================
# 🚀 动作决策 (纯内存运算)
# ==========================================
def decide_action(virtual_roots, active_path, debug_mode):
    
    def is_greater(path_a, path_b):
        if not path_b: return True
        return path_a > path_b

    def is_ancestor_or_self(path_a, path_b):
        if not path_b: return False
        if len(path_a) <= len(path_b):
            return path_a == path_b[:len(path_a)]
        return False

    def _recursive_decide(node):
        # 1. 坐标过滤
        if active_path:
            if not is_greater(node.index_path, active_path) and not is_ancestor_or_self(node.index_path, active_path):
                return False, None, None

        # 2. 容器逻辑
        if node.is_container:
            if not node.is_collapsed:
                for child in node.children:
                    res = _recursive_decide(child)
                    if res[0] or res[2]: return res
            
            if node.is_collapsed:
                should_expand = False
                if not active_path: should_expand = True
                elif is_greater(node.index_path, active_path): should_expand = True
                elif is_ancestor_or_self(node.index_path, active_path): should_expand = True
                
                if should_expand:
                    is_path_parent = active_path and is_ancestor_or_self(node.index_path, active_path) and node.index_path != active_path
                    if not node.is_completed or is_path_parent:
                        if debug_mode: print(f"🔓 [内存决策] 需展开 -> {node.text}")
                        return True, node.title_div, f"展开: {node.text}"
            
            return False, None, None

        # 3. 叶子逻辑
        
        # === 🚫 【核心修改】 遇到非视频任务，直接返回跳过 ===
        if node.should_skip:
            if debug_mode: 
                # print(f"🙈 [内存决策] 发现非视频任务({node.text}) -> 强制跳过")
                pass
            return False, None, None

        # === 锚点本身的处理 ===
        if active_path and node.index_path == active_path:
            parent_complete = node.parent and node.parent.is_completed
            
            if node.is_completed or parent_complete:
                if debug_mode: print(f"✅ [内存决策] 任务完成 -> 寻找下一个")
                return False, None, None 

            if node.is_video:
                return False, None, f"正在播放: {node.text}"
            else:
                if debug_mode: print(f"⏩ [内存决策] 非视频Active -> 跳过")
                return False, None, None
        
        # === 未完成的未来任务 ===
        if not node.is_completed:
            if "点击下方继续学习" in node.text: return False, None, None
            if debug_mode: print(f"👆 [内存决策] 发现任务 -> {node.text}")
            return True, node.title_div, f"进入: {node.text}"

        return False, None, None

    # 主循环
    for node in virtual_roots:
        res = _recursive_decide(node)
        if res[0] or res[2]: return res
        
    return False, None, "所有任务已完成"

def get_navigation_action(page, quiet=True):
    debug_mode = not quiet
    if debug_mode: print(f"\n🌳 [极速模式] 开始一次性构建内存树...")
    
    try: current_url = page.url
    except: current_url = ""

    catolog = page.ele('css:#catologOuter > ul.rank-1')
    if not catolog: return False, None, "未找到目录"
    top_lis = catolog.eles('xpath:./li')

    virtual_tree, active_path = build_tree_and_find_anchor(page, top_lis, current_url)
    
    if debug_mode:
        if active_path: print(f"⚓ 内存锚点: {active_path}")
        else: print("⚠️ 无锚点，全量检索")

    return decide_action(virtual_tree, active_path, debug_mode)