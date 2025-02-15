import streamlit as st
from dynamodb_manager import DynamoDBManager
from datetime import datetime, timedelta
import pandas as pd

def get_latest_grades():
    db = DynamoDBManager()
    yesterday = (datetime.now() - timedelta(days=1)).replace(microsecond=0).isoformat()
    response = db.table.scan(
        FilterExpression='#date >= :yesterday',
        ExpressionAttributeNames={'#date': 'Date'},
        ExpressionAttributeValues={':yesterday': yesterday}
    )
    items = response.get('Items', [])
    if not items:
        return None
    
    return sorted(items, key=lambda x: x['Date'], reverse=True)[0]['Data']

def display_grades_tree(grades_data):
    for course_name, course_data in grades_data.items():
        with st.expander(f"{course_name} ({course_data['course_grade']})"):
            for period_name, period_data in course_data['periods'].items():
                st.subheader(f"{period_name} - {period_data['period_grade']}")
                
                for category_name, category_data in period_data['categories'].items():
                    st.write(f"**{category_name} - {category_data['category_grade']}**")
                    
                    # Create a DataFrame for assignments in this category
                    assignments = category_data['assignments']
                    if assignments:
                        df = pd.DataFrame(
                            [[a['title'], a['grade']] for a in assignments],
                            columns=['Assignment', 'Grade']
                        )
                        st.dataframe(df, hide_index=True)
                st.divider()

def main():
    st.title('Schoology Grades')
    
    grades_data = get_latest_grades()
    if not grades_data:
        st.error('No recent grades data available')
        return
    
    display_grades_tree(grades_data)

if __name__ == "__main__":
    main() 