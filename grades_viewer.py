from nicegui import ui
from dynamodb_manager import DynamoDBManager
from datetime import datetime, timedelta

def build_grade_tree(grades_data):
    tree = []
    for course_name, course_data in grades_data.items():
        course = {
            'id': course_name,
            'label': f"{course_name} ({course_data['course_grade']})",
            'children': []
        }
        
        for period_name, period_data in course_data['periods'].items():
            period = {
                'id': period_name,
                'label': f"{period_name} - {period_data['period_grade']}",
                'children': []
            }
            
            for category_name, category_data in period_data['categories'].items():
                category = {
                    'id': category_name,
                    'label': f"{category_name} - {category_data['category_grade']}",
                    'children': []
                }
                
                for assignment in category_data['assignments']:
                    assignment_node = {
                        'id': assignment['title'],
                        'label': f"{assignment['title']} - {assignment['grade']}"
                    }
                    category['children'].append(assignment_node)
                    
                period['children'].append(category)
            course['children'].append(period)
        tree.append(course)
    return tree

def get_latest_grades():
    db = DynamoDBManager()
    # Get timestamp for 24 hours ago
    yesterday = (datetime.now() - timedelta(days=1)).replace(microsecond=0).isoformat()
    # Query for latest entry
    response = db.table.scan(
        FilterExpression='#date >= :yesterday',
        ExpressionAttributeNames={'#date': 'Date'},
        ExpressionAttributeValues={':yesterday': yesterday}
    )
    items = response.get('Items', [])
    if not items:
        return None
    
    # Sort by date and get the latest
    latest_item = sorted(items, key=lambda x: x['Date'], reverse=True)[0]
    return latest_item['Data']

@ui.page('/')
def main():
    ui.label('Schoology Grades').classes('text-2xl font-bold mb-4')
    
    grades_data = get_latest_grades()
    if not grades_data:
        ui.label('No recent grades data available').classes('text-red-500')
        return
    
    with ui.card().classes('w-full'):
        tree_data = build_grade_tree(grades_data)
        ui.tree([
            {'id': 'root', 'label': 'All Courses', 'children': tree_data}
        ])

ui.run(port=8081)