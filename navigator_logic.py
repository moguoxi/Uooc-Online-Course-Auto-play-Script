# navigator_logic.py
import re
from DrissionPage import ChromiumPage, ChromiumOptions

# ==========================================
# 🛠️ 虚拟节点类 (内存运算)
# ==========================================
class VirtualItem:
    def __init__(self, element, index_path, current_url):
        self.element = element 
        self.index_path = index_path
        
        # 1. 获取基础属性
        self.class_attr = element.attr('class') or ""
        
        # 2. 解析标题部分
        # 如果元素本身就是 basic (资源节点)，直接使用自己
        if 'basic' in self.class_attr:
            self.title_div = element
        else:
            # 否则查找子级 basic (章节 li 节点)
            self.title_div = element.ele('xpath:./div[contains(@class, "basic")]', timeout=0.01)
        
        if self.title_div:
            self.text = self.title_div.text.replace('\n', ' ').strip()
            self.href = self.title_div.attr('href') or ""
            # 获取 title 的 class 以判断 complete 状态
            self.title_class = self.title_div.attr('class') or ""
        else:
            self.text = "Unknown"
            self.href = ""
            self.title_class = ""
            
        # 3. 状态属性
        # 注意：complete 状态通常在 title_div 上
        self.is_completed = "complete" in self.title_class and "uncomplete" not in self.title_class
        self.is_active = "active" in self.title_class
        self.is_unopen = "unopen" in self.class_attr
        
        # 4. 锚点判定
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
        self.child_res = []
        self.child_ul = []
        
        # 仅在 li 节点下查找子结构
        if element.tag == 'li':
            self.child_res = element.eles('xpath:./div[contains(@class, "resourcelist")]/div[contains(@class, "basic")]', timeout=0.01)
            self.child_ul = element.eles('xpath:./ul/li', timeout=0.01)
        
        has_arrow = bool(self.title_div.ele('css:.icon-xiangxia, .icon-xiangshang', timeout=0.01)) if self.title_div else False
        
        self.is_container = bool(self.child_res or self.child_ul or has_arrow)
        self.is_collapsed = self.is_container and (self.is_unopen or (not self.child_res and not self.child_ul))
        
        # 6. 视频判定
        self.is_video = False
        if not self.is_container and self.title_div:
            has_icon = bool(self.title_div.ele('css:.icon-video', timeout=0.01))
            has_text = "视频" in self.text
            self.is_video = has_icon or has_text

# ==========================================
# 🌳 内存树构建与遍历
# ==========================================
def build_tree_and_find_anchor(page, root_lis, current_url):
    virtual_roots = []
    active_path = None
    
    def _recursive_build(element, current_path):
        nonlocal active_path
        node = VirtualItem(element, current_path, current_url)
        
        if node.is_self_active:
            active_path = current_path
            
        node.children = []
        child_counter = 0
        
        for res_div in node.child_res:
            child_counter += 1
            child_path = current_path + [child_counter]
            child_node = _recursive_build(res_div, child_path)
            node.children.append(child_node)
            
        for ul_li in node.child_ul:
            child_counter += 1
            child_path = current_path + [child_counter]
            child_node = _recursive_build(ul_li, child_path)
            node.children.append(child_node)
            
        return node

    for i, li in enumerate(root_lis):
        path = [i + 1]
        v_node = _recursive_build(li, path)
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
            # A. 优先递归子项
            if not node.is_collapsed:
                for child in node.children:
                    res = _recursive_decide(child)
                    if res[0] or res[2]: return res
            
            # B. 展开逻辑
            if node.is_collapsed:
                should_expand = False
                if not active_path: should_expand = True
                elif is_greater(node.index_path, active_path): should_expand = True
                elif is_ancestor_or_self(node.index_path, active_path): should_expand = True
                
                if should_expand:
                    # 如果是必经之路(父级)，或者未完成的未来节点，则展开
                    is_path_parent = active_path and is_ancestor_or_self(node.index_path, active_path) and node.index_path != active_path
                    if not node.is_completed or is_path_parent:
                        if debug_mode: print(f"🔓 [内存决策] 需展开 -> {node.text}")
                        return True, node.title_div, f"展开: {node.text}"
            
            return False, None, None

        # 3. 叶子逻辑
        
        # === [关键] 锚点本身的处理 ===
        if active_path and node.index_path == active_path:
            
            # 【核心修复】如果当前锚点已经 Completed，说明视频刚看完
            # 这时绝不能返回"正在播放"，而是应该返回 False (跳过)
            # 这样循环就会继续寻找 active_path 之后的下一个节点
            if node.is_completed:
                if debug_mode: print(f"✅ [内存决策] 当前视频已完成 -> 寻找下一个")
                return False, None, None 

            # 如果未完成且是视频 -> 正在播放
            if node.is_video:
                return False, None, f"正在播放: {node.text}"
            else:
                if debug_mode: print(f"⏩ [内存决策] Active非视频 -> 跳过")
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

if __name__ == "__main__":
    print("===========================================")
    print("   导航逻辑独立调试工具 (Completed Skip Fix)")
    print("===========================================")
    co = ChromiumOptions().set_local_port(9222)
    try:
        page = ChromiumPage(co)
        print(f"✅ 已连接页面: {page.latest_tab.title}")
        
        import time
        t0 = time.time()
        found, target, desc = get_navigation_action(page.latest_tab, quiet=False)
        t1 = time.time()
        
        print(f"⏱️ 耗时: {t1-t0:.4f}秒")
        if found: print(f"🎯 决策: [点击] -> {desc}")
        elif desc: print(f"⏸️ 决策: [等待] -> {desc}")
        else: print("🎉 决策: [完成]")
    except Exception as e: print(f"❌ 错误: {e}")