def load_workflow():
    workflow_path = "/comfyui/workflow.json"
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
            print(f"✅ Workflow loaded from {workflow_path}")
            
            # ДИАГНОСТИКА
            print(f"📋 Тип workflow: {type(workflow)}")
            if isinstance(workflow, dict):
                print(f"📋 Ключи верхнего уровня: {list(workflow.keys())}")
                
                # Проверяем UI-формат
                if 'nodes' in workflow:
                    print(f"📋 Это UI-формат. Найдено nodes: {len(workflow['nodes'])}")
                    # Ищем ноды 134 и 148
                    found_134 = False
                    found_148 = False
                    for node in workflow['nodes']:
                        if node.get('id') == 134:
                            print(f"🔍 Найдена нода 134: {node.get('type')}")
                            print(f"   widgets_values: {node.get('widgets_values')}")
                            found_134 = True
                        if node.get('id') == 148:
                            print(f"🔍 Найдена нода 148: {node.get('type')}")
                            print(f"   widgets_values: {node.get('widgets_values')}")
                            found_148 = True
                    if not found_134:
                        print("❌ Нода 134 НЕ НАЙДЕНА в nodes!")
                    if not found_148:
                        print("❌ Нода 148 НЕ НАЙДЕНА в nodes!")
                
                # Проверяем API-формат
                elif '134' in workflow:
                    print(f"📋 Это API-формат. Найдена нода 134: {workflow['134'].get('class_type')}")
                else:
                    print("❌ Неизвестный формат workflow")
            
            return workflow
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        raise
