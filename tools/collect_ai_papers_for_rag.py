#!/usr/bin/env python3
import html
import json
import re
import time
import urllib.request
from pathlib import Path

import fitz


OUT_DIR = Path("/Users/hb02803/Desktop/data/ai_papers")
PDF_DIR = OUT_DIR / "pdfs"
TEXT_DIR = OUT_DIR / "texts"
META_DIR = OUT_DIR / "metadata"
TRAIN_DIR = OUT_DIR / "training"

PAPERS = [
    {
        "id": "1706.03762",
        "topic_cn": "Transformer 架构",
        "terms": ["自注意力机制", "多头注意力", "位置编码", "编码器-解码器结构"],
    },
    {
        "id": "1810.04805",
        "topic_cn": "BERT 预训练语言模型",
        "terms": ["Masked Language Model", "双向编码器", "下一句预测", "微调范式"],
    },
    {
        "id": "2004.04906",
        "topic_cn": "Dense Passage Retrieval",
        "terms": ["双编码器检索", "稠密向量召回", "开放域问答", "负样本训练"],
    },
    {
        "id": "2005.11401",
        "topic_cn": "检索增强生成 RAG",
        "terms": ["参数化记忆", "非参数化记忆", "检索器和生成器联合建模", "知识密集型任务"],
    },
    {
        "id": "2007.01282",
        "topic_cn": "Fusion-in-Decoder 开放域问答",
        "terms": ["Fusion-in-Decoder", "多文档融合", "开放域问答", "生成式问答"],
    },
    {
        "id": "2106.09685",
        "topic_cn": "LoRA 参数高效微调",
        "terms": ["低秩适配", "参数高效微调", "冻结预训练权重", "大模型微调成本"],
    },
    {
        "id": "2201.11903",
        "topic_cn": "Chain-of-Thought Prompting",
        "terms": ["思维链提示", "中间推理步骤", "大模型推理能力", "少样本推理"],
    },
    {
        "id": "2210.03629",
        "topic_cn": "ReAct 推理与行动",
        "terms": ["推理和行动协同", "工具调用", "轨迹生成", "交互式问答"],
    },
    {
        "id": "2212.10496",
        "topic_cn": "HyDE 假设文档嵌入",
        "terms": ["假设文档", "零样本稠密检索", "向量检索查询改写", "无监督检索"],
    },
    {
        "id": "2302.13971",
        "topic_cn": "LLaMA 基础语言模型",
        "terms": ["基础语言模型", "模型规模扩展", "训练数据配比", "高效推理"],
    },
    {
        "id": "2310.06825",
        "topic_cn": "Mistral 7B",
        "terms": ["滑动窗口注意力", "分组查询注意力", "7B 语言模型", "推理效率"],
    },
    {
        "id": "2310.11511",
        "topic_cn": "Self-RAG 自反思检索增强生成",
        "terms": ["自反思检索", "反思标记", "检索是否必要", "生成内容自评估"],
    },
    {
        "id": "2404.16130",
        "topic_cn": "GraphRAG 图检索增强生成",
        "terms": ["图结构检索", "社区摘要", "全局问答", "查询聚焦摘要"],
    },
    {
        "id": "2501.12948",
        "topic_cn": "DeepSeek-R1 推理模型",
        "terms": ["强化学习推理", "自我反思", "推理蒸馏", "可验证任务"],
    },
]


def ensure_dirs():
    for path in [PDF_DIR, TEXT_DIR, META_DIR, TRAIN_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def request_url(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Codex local RAG dataset builder (contact: local-user)",
            "Accept": "text/html,application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def meta_value(page: str, name: str) -> str:
    pattern = rf'<meta\s+name="{re.escape(name)}"\s+content="(.*?)"\s*/?>'
    match = re.search(pattern, page, flags=re.I | re.S)
    return html.unescape(match.group(1)).strip() if match else ""


def meta_values(page: str, name: str):
    pattern = rf'<meta\s+name="{re.escape(name)}"\s+content="(.*?)"\s*/?>'
    return [html.unescape(m).strip() for m in re.findall(pattern, page, flags=re.I | re.S)]


def safe_name(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")[:120]


def extract_pdf_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for index, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append(f"\n\n[page {index}]\n{text}")
    return "\n".join(pages).strip()


def collect_papers():
    manifest = []
    for paper in PAPERS:
        arxiv_id = paper["id"]
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        print(f"fetch {arxiv_id} abs")
        page = request_url(abs_url).decode("utf-8", "ignore")
        title = meta_value(page, "citation_title") or arxiv_id
        abstract = meta_value(page, "citation_abstract")
        authors = meta_values(page, "citation_author")
        published = meta_value(page, "citation_date")
        pdf_url = meta_value(page, "citation_pdf_url") or f"https://arxiv.org/pdf/{arxiv_id}"
        base = f"{arxiv_id}_{safe_name(title)}"
        pdf_path = PDF_DIR / f"{base}.pdf"
        txt_path = TEXT_DIR / f"{base}.txt"

        if not pdf_path.exists() or pdf_path.stat().st_size < 1000:
            print(f"download {arxiv_id} pdf")
            pdf_path.write_bytes(request_url(pdf_url))
            time.sleep(1.0)

        if not txt_path.exists() or txt_path.stat().st_size < 1000:
            print(f"extract {arxiv_id} text")
            text = extract_pdf_text(pdf_path)
            header = [
                f"title: {title}",
                f"arxiv_id: {arxiv_id}",
                f"topic_cn: {paper['topic_cn']}",
                f"url: {abs_url}",
                f"pdf_url: {pdf_url}",
                f"published: {published}",
                f"authors: {', '.join(authors[:12])}",
                "",
                "abstract:",
                abstract,
                "",
                "full_text:",
            ]
            txt_path.write_text("\n".join(header) + "\n" + text, encoding="utf-8")

        manifest.append(
            {
                "arxiv_id": arxiv_id,
                "title": title,
                "topic_cn": paper["topic_cn"],
                "terms": paper["terms"],
                "authors": authors,
                "published": published,
                "abstract": abstract,
                "url": abs_url,
                "pdf_url": pdf_url,
                "pdf_path": str(pdf_path),
                "text_path": str(txt_path),
            }
        )
        time.sleep(0.5)
    return manifest


def build_professional_queries(manifest):
    templates = [
        "知识库里《{title}》主要解决什么问题？",
        "请根据论文资料解释一下{topic_cn}的核心思想。",
        "如果用户问{topic_cn}，应该从哪篇资料检索？",
        "论文《{title}》中提到的关键方法适合解决哪些 AI 项目问题？",
        "请结合资料说明{term}在{topic_cn}中的作用。",
        "资料里关于{term}的定义和实现思路是什么？",
        "在 RAG 系统中，{topic_cn}相关内容应该如何切片入库？",
        "这批论文资料中有没有介绍{term}？",
        "请从知识库检索{topic_cn}的技术路线。",
        "根据《{title}》，有哪些适合作为 AI 项目的实验指标？",
        "我想做一个和{topic_cn}相关的项目，知识库里有哪些依据？",
        "论文资料中{topic_cn}和 RAG 检索增强有什么关系？",
        "请基于已收集论文回答：{term}为什么重要？",
    ]
    queries = []
    for item in manifest:
        for idx, template in enumerate(templates):
            term = item["terms"][idx % len(item["terms"])]
            queries.append(
                {
                    "query": template.format(
                        title=item["title"], topic_cn=item["topic_cn"], term=term
                    ),
                    "label": "专业咨询",
                    "source_arxiv_id": item["arxiv_id"],
                    "source_title": item["title"],
                }
            )
    return queries


def build_general_queries(count):
    templates = [
        "请解释一下什么是{concept}，回答控制在三句话内。",
        "{concept}和{concept2}有什么区别？",
        "用 Python 写一个{task}的简单示例。",
        "如何排查{issue}，请列出常见原因。",
        "请给出{topic}的入门学习路线。",
        "计算：{math_expr}，只给出结果和简要过程。",
        "写一个 SQL 查询，统计{sql_task}。",
        "请解释{algo}算法的时间复杂度和适用场景。",
        "Linux 里如何使用 {cmd} 命令？给一个例子。",
        "Java 中{java_topic}是什么意思？",
        "请比较{concept}在实际开发中的优点和局限。",
        "给我一个关于{topic}的面试题和参考答案。",
        "用 JavaScript 实现{task}应该怎么写？",
        "数据库出现{issue}时该怎么定位？",
        "{algo}和{concept2}可以放在一起理解吗？为什么？",
    ]
    concepts = [
        "RESTful API", "Docker", "Kubernetes", "哈希表", "二分查找", "事务 ACID",
        "OAuth2", "消息队列", "缓存穿透", "负载均衡", "索引", "微服务",
        "HTTPS", "DNS 解析", "并发和并行", "设计模式", "单元测试", "DevOps",
    ]
    tasks = [
        "读取 CSV 文件", "调用 HTTP 接口", "合并两个列表", "遍历目录文件",
        "统计词频", "生成随机密码", "解析 JSON", "连接 MySQL 数据库",
    ]
    issues = ["接口超时", "内存泄漏", "数据库慢查询", "容器启动失败", "Git 冲突", "跨域请求失败"]
    topics = ["Python 后端开发", "前端工程化", "数据结构", "软件测试", "Linux 运维", "数据库优化"]
    math_exprs = ["128 * 256", "1/3 + 1/6", "2 的 10 次方", "从 1 加到 100", "sqrt(144)", "15% 的 260"]
    sql_tasks = ["每个班级的学生人数", "每个用户的订单数量", "每月销售额", "每个商品的平均评分"]
    algos = ["快速排序", "广度优先搜索", "动态规划", "Dijkstra", "归并排序", "LRU 缓存"]
    cmds = ["grep", "find", "tar", "ps", "chmod", "curl", "ssh", "scp"]
    java_topics = ["泛型", "反射", "线程池", "接口", "异常处理", "CompletableFuture", "JVM 垃圾回收"]

    modifiers = ["基础版", "进阶版", "面试场景", "项目实践场景", "新手视角", "排错视角"]

    queries = []
    seen = set()
    i = 0
    max_attempts = max(count * 100, 1000)
    while len(queries) < count and i < max_attempts:
        template = templates[i % len(templates)]
        concept = concepts[(i * 7 + 1) % len(concepts)]
        concept2 = concepts[(i * 11 + 4) % len(concepts)]
        if concept2 == concept:
            concept2 = concepts[(i * 11 + 5) % len(concepts)]
        query = template.format(
            concept=concept,
            concept2=concept2,
            task=tasks[(i * 5 + 2) % len(tasks)],
            issue=issues[(i * 7 + 3) % len(issues)],
            topic=topics[(i * 5 + 1) % len(topics)],
            math_expr=math_exprs[(i * 7 + 4) % len(math_exprs)],
            sql_task=sql_tasks[(i * 3 + 2) % len(sql_tasks)],
            algo=algos[(i * 5 + 3) % len(algos)],
            cmd=cmds[(i * 7 + 1) % len(cmds)],
            java_topic=java_topics[(i * 5 + 4) % len(java_topics)],
        )
        if i >= len(templates):
            query = f"{query}（{modifiers[(i // len(templates)) % len(modifiers)]}）"
        if query not in seen:
            seen.add(query)
            queries.append({"query": query, "label": "通用知识"})
        i += 1
    while len(queries) < count:
        index = len(queries) + 1
        query = f"请给出一个通用软件工程问题的简短回答示例，编号 {index}。"
        if query not in seen:
            seen.add(query)
            queries.append({"query": query, "label": "通用知识"})
    return queries


def write_training_files(manifest):
    professional = build_professional_queries(manifest)
    general = build_general_queries(len(professional))
    paired = []
    for g, p in zip(general, professional):
        paired.append(g)
        paired.append(p)

    jsonl_text = "\n".join(json.dumps(row, ensure_ascii=False) for row in paired) + "\n"
    jsonl_path = TRAIN_DIR / "bert_ai_rag_classifier_364.jsonl"
    compat_json_path = TRAIN_DIR / "bert_ai_rag_classifier_364.json"
    array_json_path = TRAIN_DIR / "bert_ai_rag_classifier_364_array.json"
    jsonl_path.write_text(jsonl_text, encoding="utf-8")
    compat_json_path.write_text(jsonl_text, encoding="utf-8")
    array_json_path.write_text(json.dumps(paired, ensure_ascii=False, indent=2), encoding="utf-8")

    stats = {
        "total": len(paired),
        "labels": {
            "通用知识": sum(1 for row in paired if row["label"] == "通用知识"),
            "专业咨询": sum(1 for row in paired if row["label"] == "专业咨询"),
        },
        "jsonl_path": str(jsonl_path),
        "compat_json_path": str(compat_json_path),
        "array_json_path": str(array_json_path),
    }
    (TRAIN_DIR / "training_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return stats


def write_readme(manifest, stats):
    lines = [
        "# AI Papers RAG Dataset",
        "",
        "用途：开放论文资料收集、后续切片、向量化入库，以及 BERT 查询分类器训练语料扩充。",
        "",
        "目录：",
        "- `pdfs/`: 原始 PDF",
        "- `texts/`: 从 PDF 抽取出的可切片纯文本，文件头包含标题、arXiv ID、摘要和来源 URL",
        "- `metadata/ai_papers_manifest.json`: 论文元数据和本地路径",
        "- `training/bert_ai_rag_classifier_364.jsonl`: JSONL 训练语料",
        "- `training/bert_ai_rag_classifier_364.json`: 与现有训练代码命名习惯兼容的 JSONL 语料",
        "- `training/bert_ai_rag_classifier_364_array.json`: 标准 JSON 数组格式，方便人工浏览或其他工具读取",
        "",
        "分类标签沿用当前项目代码：",
        "- `通用知识`: 不需要查本地知识库，直接由大模型回答",
        "- `专业咨询`: 需要进入本地 RAG 检索，覆盖已收集 AI 论文/项目资料相关问题",
        "",
        f"训练语料统计：总计 {stats['total']} 条，通用知识 {stats['labels']['通用知识']} 条，专业咨询 {stats['labels']['专业咨询']} 条。",
        "",
        "论文来源：",
    ]
    for item in manifest:
        lines.append(f"- {item['arxiv_id']} | {item['title']} | {item['url']}")
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ensure_dirs()
    manifest = collect_papers()
    manifest_path = META_DIR / "ai_papers_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    stats = write_training_files(manifest)
    write_readme(manifest, stats)
    print(json.dumps({"papers": len(manifest), "stats": stats}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
