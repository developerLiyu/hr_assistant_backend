import os
import asyncio
import traceback
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List
import httpx
from httpx import HTTPStatusError
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility, MilvusClient
from pymilvus.milvus_client import IndexParams

# Milvus配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "117.72.112.16")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", 19530))
MILVUS_DB_NAME_RESUME = os.getenv("MILVUS_DB_NAME_RESUME", "resume_db")
MILVUS_ALIAS_NAME_RESUME = os.getenv("MILVUS_ALIAS_NAME_RESUME", "resume")
MILVUS_COLLECTION_NAME_RESUME = os.getenv("MILVUS_COLLECTION_NAME_RESUME", "resume_embeddings")

# 通义千问Embedding配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v1")
EMBEDDING_DIM = 1536  # 固定1536维

# 创建全局线程池
executor = ThreadPoolExecutor(max_workers=5)


def init_milvus():
    """
    适配：pymilvus 2.6.11 官方最新 API（MilvusClient）
    功能：连接 → 数据库管理 → 集合/索引 → 加载（零报错）
    """
    try:
        # 1. 创建 MilvusClient 客户端（2.6.x 唯一标准写法）
        client = MilvusClient(
            uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}",
            alias=MILVUS_ALIAS_NAME_RESUME  # 连接别名
        )
        print(f"✅ 云服务器 Milvus 连接成功 | 别名：{MILVUS_ALIAS_NAME_RESUME}")

        # 2. 数据库操作（2.6.x 官方标准 API）
        # 获取所有数据库列表
        db_list = client.list_databases()
        if MILVUS_DB_NAME_RESUME not in db_list:
            # 创建自定义数据库
            client.create_database(MILVUS_DB_NAME_RESUME)
            print(f"🆕 自动创建数据库：{MILVUS_DB_NAME_RESUME}")
        else:
            print(f"✅ 数据库已存在：{MILVUS_DB_NAME_RESUME}")

        # 切换到目标数据库（后续操作都在该库下）
        client.using_database(MILVUS_DB_NAME_RESUME)
        print(f"✅ 已切换工作数据库：{MILVUS_DB_NAME_RESUME}")

        # 3. 集合操作
        # 检查集合是否存在
        if client.has_collection(collection_name=MILVUS_COLLECTION_NAME_RESUME):
            print(f"✅ 集合已存在：{MILVUS_COLLECTION_NAME_RESUME}")

            # ===================== 智能检查并重建索引 =====================
            try:
                # 1. 获取集合的索引信息
                index_info = client.describe_index(
                    collection_name=MILVUS_COLLECTION_NAME_RESUME,
                    index_name=""  # 空字符串表示获取默认索引
                )

                # 2. 检查当前索引的度量类型
                current_metric_type = index_info.get('metric_type', '')
                print(f"📊 当前索引度量类型：{current_metric_type}")

                # 3. 如果不是 COSINE，则重建索引
                if current_metric_type != "COSINE":
                    print(f"🔄 检测到度量类型为 {current_metric_type}，需要重建为 COSINE")

                    # 卸载集合（删除索引前必须卸载）
                    client.release_collection(collection_name=MILVUS_COLLECTION_NAME_RESUME)
                    print("🔄 已卸载集合")

                    # 删除旧的向量索引
                    client.drop_index(
                        collection_name=MILVUS_COLLECTION_NAME_RESUME,
                        index_name=index_info.get('index_name', '')
                    )
                    print("🗑️ 已删除旧索引")

                    # 创建新的 COSINE 度量类型的索引
                    new_index_params = IndexParams()
                    new_index_params.add_index(
                        index_type="IVF_FLAT",
                        metric_type="COSINE",
                        field_name="embedding",
                        params={"nlist": 128}
                    )
                    client.create_index(
                        collection_name=MILVUS_COLLECTION_NAME_RESUME,
                        index_params=new_index_params
                    )
                    print("✅ 已创建新的 COSINE 度量类型索引")
                else:
                    print("✅ 索引已是 COSINE 类型，无需重建")

            except Exception as e:
                # 如果索引不存在或获取失败，创建新索引
                print(f"⚠️ 获取索引信息失败：{str(e)}，尝试创建 COSINE 索引")
                try:
                    # 先尝试卸载集合
                    try:
                        client.release_collection(collection_name=MILVUS_COLLECTION_NAME_RESUME)
                    except:
                        pass

                    # 尝试删除可能存在的旧索引
                    try:
                        client.drop_index(
                            collection_name=MILVUS_COLLECTION_NAME_RESUME,
                            index_name=""
                        )
                    except:
                        pass

                    # 创建新索引
                    new_index_params = IndexParams()
                    new_index_params.add_index(
                        index_type="IVF_FLAT",
                        metric_type="COSINE",
                        field_name="embedding",
                        params={"nlist": 128}
                    )
                    client.create_index(
                        collection_name=MILVUS_COLLECTION_NAME_RESUME,
                        index_params=new_index_params
                    )
                    print("✅ 已创建 COSINE 索引")
                except Exception as e2:
                    print(f"⚠️ 索引可能已存在：{str(e2)}")
        else:
            print(f"🆕 创建集合：{MILVUS_COLLECTION_NAME_RESUME}")
            # 定义集合字段
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True, comment="自增主键"),
                FieldSchema(name="resume_id", dtype=DataType.INT64, comment="关联简历ID"),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM, comment="文本向量")
            ]
            # 集合结构
            schema = CollectionSchema(fields=fields, description="简历向量检索集合")
            # 创建集合
            client.create_collection(
                collection_name=MILVUS_COLLECTION_NAME_RESUME,
                schema=schema,
                description="简历向量检索集合"
            )

            # ===================== 核心修复：使用 IndexParams 创建索引 =====================
            # 1. 初始化 IndexParams 对象（2.6.11 强制要求）
            index_params = IndexParams()
            # 2. 设置索引参数（严格匹配 IVF_FLAT + COSINE 配置）
            index_params.add_index(
                index_type="IVF_FLAT",
                metric_type="COSINE",
                field_name="embedding",
                params={"nlist": 128}
            )
            # 3. 创建向量索引（传入标准化的 IndexParams 对象）
            client.create_index(
                collection_name=MILVUS_COLLECTION_NAME_RESUME,
                index_params=index_params  # 替换原字典参数
            )
            print("✅ 向量索引创建完成（IndexParams 类型适配）")


        # 4. 加载集合到内存（支持读写/检索）
        client.load_collection(collection_name=MILVUS_COLLECTION_NAME_RESUME)
        print("✅ 集合已加载到内存，支持读写/检索")

        print("\n🎉 Milvus 初始化全部完成！")
        return client

    # 完整异常捕获
    except Exception as e:
        print(f"\n❌ Milvus 初始化失败：{type(e).__name__}")
        print(f"❌ 错误信息：{str(e)}")
        print("="*60)
        traceback.print_exc()
        print("="*60)
        raise RuntimeError(f"Milvus 初始化异常：{str(e)}") from e



async def async_insert_embedding(resume_id: int, embedding: List[float]) -> int:
    """异步插入向量到Milvus，返回自增主键ID"""
    try:
        # 获取当前异步事件循环
        loop = asyncio.get_running_loop()

        # 在线程池中初始化Milvus客户端（避免阻塞异步事件循环）
        client = await loop.run_in_executor(executor, init_milvus)

        print(f"获取客户端成功：{type(client)}")

        # 构造要插入的实体数据，包含简历ID和对应的向量嵌入
        entities = [
            {"resume_id": resume_id, "embedding": embedding}
        ]

        # 在线程池中执行向量插入操作
        insert_res = await loop.run_in_executor(
            executor,
            lambda: client.insert(collection_name=MILVUS_COLLECTION_NAME_RESUME, data=entities)
        )

        print(f"插入数据成功：{insert_res}")

        # 刷新集合，确保数据持久化到磁盘
        await loop.run_in_executor(
            executor,
            lambda: client.flush(collection_name=MILVUS_COLLECTION_NAME_RESUME)
        )

        print(f"刷新集合成功")

        # 检查是否有数据成功插入
        if not insert_res.get('insert_count', 0):
            raise RuntimeError("Milvus数据插入失败，未插入任何数据")

        # 返回Milvus自动生成的主键ID（第一条记录的ID）
        return insert_res.get('ids', [])[0]

    except Exception as e:
        # 捕获所有异常并包装为RuntimeError，保留原始堆栈信息
        raise RuntimeError(f"Milvus异步插入向量异常: {str(e)}") from e

async def async_upsert_embedding(milvus_id: int, resume_id: int, embedding: List[float]) -> int:
    """异步更新向量到Milvus，返回自增主键ID"""
    try:
        # 获取当前异步事件循环
        loop = asyncio.get_running_loop()

        # 在线程池中初始化Milvus客户端（避免阻塞异步事件循环）
        client = await loop.run_in_executor(executor, init_milvus)

        print(f"获取客户端成功：{type(client)}")

        # 构造要插入的实体数据，包含简历ID和对应的向量嵌入
        entities = [
            {"id": milvus_id, "resume_id": resume_id, "embedding": embedding}
        ]

        # 在线程池中执行向量插入操作
        upsert_res = await loop.run_in_executor(
            executor,
            lambda: client.upsert(collection_name=MILVUS_COLLECTION_NAME_RESUME, data=entities)
        )

        print(f"更新数据成功：{upsert_res}")

        # 刷新集合，确保数据持久化到磁盘
        await loop.run_in_executor(
            executor,
            lambda: client.flush(collection_name=MILVUS_COLLECTION_NAME_RESUME)
        )

        print(f"刷新集合成功")

        # 检查总影响行数（插入数 + 更新数）
        insert_count = upsert_res.get('insert_count', 0)
        upsert_count = upsert_res.get('upsert_count', 0)
        total_affected = insert_count + upsert_count

        if not total_affected:
            raise RuntimeError("Milvus数据upsert失败，未影响任何数据")

        print(f"Upsert结果 - 插入: {insert_count}, 更新: {upsert_count}, 总影响: {total_affected}")

        # 返回主键ID列表中的第一个ID
        ids = upsert_res.get('ids', [])
        if not ids:
            raise RuntimeError("Milvus upsert成功但未返回ID")

        return ids[0]

    except Exception as e:
        # 捕获所有异常并包装为RuntimeError，保留原始堆栈信息
        raise RuntimeError(f"Milvus异步更新向量异常: {str(e)}") from e


# 删除集合中的一条记录
async def async_delete_embedding(milvus_id: int) -> bool:
    """异步删除Milvus集合中的一条记录，返回是否删除成功"""
    try:
        # 获取当前异步事件循环
        loop = asyncio.get_running_loop()

        # 在线程池中初始化Milvus客户端（避免阻塞异步事件循环）
        client = await loop.run_in_executor(executor, init_milvus)

        print(f"获取客户端成功：{type(client)}")

        # 构造删除条件表达式（通过主键ID删除）
        delete_expr = f"id == {milvus_id}"

        # 在线程池中执行删除操作
        delete_res = await loop.run_in_executor(
            executor,
            lambda: client.delete(collection_name=MILVUS_COLLECTION_NAME_RESUME, filter=delete_expr)
        )

        print(f"删除数据结果：{delete_res}")

        # 刷新集合，确保删除操作持久化到磁盘
        await loop.run_in_executor(
            executor,
            lambda: client.flush(collection_name=MILVUS_COLLECTION_NAME_RESUME)
        )

        print(f"刷新集合成功")

        # 检查删除计数
        delete_count = delete_res.get('delete_count', 0)

        if not delete_count:
            print(f"⚠️ 未找到ID为 {milvus_id} 的记录")
            return False

        print(f"✅ 成功删除 {delete_count} 条记录")
        return True

    except Exception as e:
        # 捕获所有异常并包装为RuntimeError，保留原始堆栈信息
        raise RuntimeError(f"Milvus异步删除向量异常: {str(e)}") from e



# 搜索集合中的数据
async def async_search_embedding(yaoqiu_message_embedding: List[float], top_n: int = 10) -> List[dict]:
    """异步搜索Milvus集合中的相似向量

    Args:
        yaoqiu_message_embedding: 查询文本的向量嵌入
        top_n: 返回最相似的top_n条记录

    Returns:
        包含resume_id和相似度值的列表，按相似度从大到小排序
        格式: [{"resume_id": 1, "similarity": 0.95}, ...]
    """
    try:
        # 获取当前异步事件循环
        loop = asyncio.get_running_loop()

        # 在线程池中初始化Milvus客户端（避免阻塞异步事件循环）
        client = await loop.run_in_executor(executor, init_milvus)

        print(f"获取客户端成功：{type(client)}")

        # 构造搜索参数
        search_params = {
            "metric_type": "COSINE",  # 使用余弦相似度
            "params": {"nprobe": 10}  # IVF_FLAT索引的搜索参数
        }

        # 执行向量搜索
        search_results = await loop.run_in_executor(
            executor,
            lambda: client.search(
                collection_name=MILVUS_COLLECTION_NAME_RESUME,
                data=[yaoqiu_message_embedding],  # 查询向量列表
                anns_field="embedding",  # 向量字段名
                search_params=search_params,
                limit=top_n,  # 返回top_n条结果
                output_fields=["resume_id"]  # 需要返回的字段
            )
        )

        print(f"搜索完成，返回结果数：{len(search_results)}")

        # 解析搜索结果
        result_list = []
        if search_results and len(search_results) > 0:
            # search_results[0] 是第一条查询向量的匹配结果
            hits = search_results[0]

            for hit in hits:
                resume_id = hit.get('entity', {}).get('resume_id')
                distance = hit.get('distance', 0.0)  # COSINE相似度范围[-1, 1]

                if resume_id is not None:
                    result_list.append({
                        "resume_id": resume_id,
                        "similarity": round(distance, 2)  # 保留2位小数
                    })

        # 按相似度从大到小排序（Milvus默认已按distance降序返回，此处确保排序）
        result_list.sort(key=lambda x: x["similarity"], reverse=True)

        print(f"✅ 搜索成功，返回 {len(result_list)} 条结果")
        return result_list

    except Exception as e:
        # 捕获所有异常并包装为RuntimeError，保留原始堆栈信息
        raise RuntimeError(f"Milvus异步搜索向量异常: {str(e)}") from e



async def async_generate_embedding(text: str) -> List[float]:
    """异步调用通义千问Embedding生成1536维向量（已修复）"""
    # 空文本直接返回零向量
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM

    # 通义千问官方Embedding接口地址
    url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json"
    }

    # ===================== 核心修复1：修正请求体JSON格式 =====================
    # 原错误写法：data = {"input": text, "model": EMBEDDING_MODEL}
    # 正确格式：input为{"texts": [文本]}，必须传text_type
    data = {
        "model": EMBEDDING_MODEL,
        "input": {
            "texts": [text.strip()]  # texts为数组，支持批量，此处单文本
        },
        # ===================== 核心修复2：补充必选参数text_type =====================
        "text_type": "document"  # 简历属于文档类，设为document；查询语句设为query
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=data)
            # 捕获HTTP状态码错误（4xx/5xx）
            resp.raise_for_status()
            result = resp.json()

            # ===================== 修复3：校验API业务错误 =====================
            if result.get("code") not in (200, None):
                raise ValueError(f"API错误：{result.get('message')}，请求ID：{result.get('request_id')}")

            # ===================== 修复4：健壮提取向量，避免索引异常 =====================
            embeddings = result.get("output", {}).get("embeddings", [])
            return embeddings[0].get("embedding", [0.0] * EMBEDDING_DIM) if embeddings else [0.0] * EMBEDDING_DIM

    # ===================== 修复5：完善异常捕获 =====================
    except HTTPStatusError as e:
        print(f"HTTP请求失败：{e.response.status_code}，响应：{e.response.text}")
        return [0.0] * EMBEDDING_DIM
    except Exception as e:
        print(f"向量生成异常：{str(e)}")
        return [0.0] * EMBEDDING_DIM


