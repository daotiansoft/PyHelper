from HttpHelper import StableAPIClient

# 使用示例
if __name__ == "__main__":
    # 1. 基本使用
    print("=== 基本使用示例 ===")
    client = StableAPIClient(
        base_url="https://jsonplaceholder.typicode.com",
        default_timeout=10
    )
    
    # 发送GET请求
    response = client.get("/posts/1")
    
    if response.is_success:
        print(f"请求成功: {response.status_code}")
        print(f"数据: {response.data}")
        print(f"耗时: {response.elapsed_time:.3f}秒")
    else:
        print(f"请求失败: {response.error_message}")
    
    # 2. 安全获取嵌套数据
    print("\n=== 安全获取数据示例 ===")
    title = client.get_safe(
        "/posts/1",
        key_path="title",
        default="默认标题"
    )
    print(f"文章标题: {title}")
    
    # 3. 发送POST请求
    print("\n=== POST请求示例 ===")
    post_data = {
        "title": "测试文章",
        "body": "测试内容",
        "userId": 1
    }
    post_response = client.post("/posts", data=post_data)
    
    if post_response.is_success:
        print(f"创建成功，ID: {post_response.data.get('id')}")
    
    # 4. 批量请求
    print("\n=== 批量请求示例 ===")
    requests_list = [
        {"method": "GET", "endpoint": "/posts/1"},
        {"method": "GET", "endpoint": "/posts/2"},
        {"method": "GET", "endpoint": "/posts/3"}
    ]
    
    batch_responses = client.batch_request(requests_list, max_concurrent=2)
    
    for i, resp in enumerate(batch_responses):
        if resp.is_success:
            print(f"请求 {i+1} 成功")
        else:
            print(f"请求 {i+1} 失败: {resp.error_message}")
    
    # 5. 查看统计信息
    print("\n=== 统计信息 ===")
    stats = client.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # 6. 错误处理示例
    print("\n=== 错误处理示例 ===")
    error_response = client.get("/nonexistent")
    if not error_response.is_success:
        print(f"预期中的错误: {error_response.status} - {error_response.error_message}")
    
    # 关闭客户端
    client.close()