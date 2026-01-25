import SafeJSON

# 使用示例
if __name__ == "__main__":
    # 示例JSON数据
    json_data = {
        "user": {
            "id": 123,
            "name": "张三",
            "email": "zhangsan@example.com",
            "age": "30",
            "is_active": "true",
            "balance": "123.456",
            "created_at": "2023-01-15 10:30:00",
            "tags": ["admin", "vip", "premium"],
            "metadata": {
                "level": "gold",
                "points": 1000
            }
        },
        "items": [
            {"id": 1, "name": "Item 1", "price": "10.50"},
            {"id": 2, "name": "Item 2", "price": "20.00"},
            {"id": 3, "name": "Item 3", "price": "30.75"}
        ],
        "settings": {
            "notifications": {
                "email": True,
                "sms": False
            }
        }
    }
    
    print("=== SafeJSON 使用示例 ===")
    
    # 1. 基本取值
    print("1. 基本取值:")
    print(f"用户名: {SafeJSON.get_string(json_data, 'user', 'name')}")
    print(f"年龄: {SafeJSON.get_int(json_data, 'user', 'age')}")
    print(f"是否激活: {SafeJSON.get_bool(json_data, 'user', 'is_active')}")
    print(f"余额: {SafeJSON.get_float(json_data, 'user', 'balance', precision=2)}")
    print(f"不存在的字段: {SafeJSON.get_string(json_data, 'user', 'phone', default='N/A')}")
    
    # 2. 路径表达式
    print("\n2. 路径表达式:")
    print(f"用户等级: {SafeJSON.get_path(json_data, 'user.metadata.level')}")
    print(f"第一个商品名: {SafeJSON.get_path(json_data, 'items[0].name')}")
    print(f"第二个商品价格: {SafeJSON.get_path(json_data, 'items.1.price')}")
    
    # 3. 列表操作
    print("\n3. 列表操作:")
    tags = SafeJSON.get_list(json_data, 'user', 'tags')
    print(f"用户标签: {tags}")
    
    # 获取商品ID列表
    item_ids = SafeJSON.get_list(json_data, 'items', item_type=lambda x: x.get('id'))
    print(f"商品ID列表: {item_ids}")
    
    # 4. 日期时间
    print("\n4. 日期时间:")
    created_at = SafeJSON.get_datetime(json_data, 'user', 'created_at')
    print(f"创建时间: {created_at}")
    
    # 5. Decimal精确计算
    print("\n5. Decimal值:")
    balance_decimal = SafeJSON.get_decimal(json_data, 'user', 'balance')
    print(f"余额(Decimal): {balance_decimal}")
    
    # 6. 数据提取
    print("\n6. 数据提取:")
    mapping = {
        "user_id": "user.id",
        "username": "user.name",
        "user_age": "user.age",
        "user_level": "user.metadata.level",
        "first_item": "items[0].name"
    }
    extracted = SafeJSON.extract(json_data, mapping)
    print(f"提取的数据: {extracted}")
    
    # 7. 安全解析
    print("\n7. 安全解析JSON:")
    json_str = '{"test": "value"}'
    parsed = SafeJSON.parse_safe(json_str, default={})
    print(f"解析结果: {parsed}")
    
    invalid_json = 'invalid json'
    parsed_invalid = SafeJSON.parse_safe(invalid_json, default={})
    print(f"无效JSON解析结果: {parsed_invalid}")