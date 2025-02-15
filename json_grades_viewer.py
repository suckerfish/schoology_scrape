import streamlit as st
from dynamodb_manager import DynamoDBManager
from datetime import datetime
import json

def get_latest_grades():
    try:
        db = DynamoDBManager()
        response = db.table.scan()
        items = response.get('Items', [])
        
        if items:
            latest_item = sorted(items, key=lambda x: x['Date'], reverse=True)[0]
            st.sidebar.success(f"Showing data from: {latest_item['Date']}")
            return latest_item['Data']
            
        st.warning("No items found in the database")
        return None
        
    except Exception as e:
        st.error(f"Error retrieving grades: {str(e)}")
        return None

def convert_to_html_tree(data, indent=0):
    """Convert JSON data to HTML with expandable sections"""
    if isinstance(data, dict):
        html = ""
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                html += f"""
                <details style="margin-left: {indent}px">
                    <summary style="padding: 5px; cursor: pointer;">
                        <span style="color: #666;">{key}</span>
                    </summary>
                    {convert_to_html_tree(value, indent + 20)}
                </details>
                """
            else:
                html += f"""
                <div style="margin-left: {indent}px; padding: 5px;">
                    <span style="color: #666;">{key}:</span> 
                    <span style="color: #333;">{value}</span>
                </div>
                """
        return html
    elif isinstance(data, list):
        html = ""
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                html += f"""
                <details style="margin-left: {indent}px">
                    <summary style="padding: 5px; cursor: pointer;">
                        <span style="color: #666;">Item {i}</span>
                    </summary>
                    {convert_to_html_tree(item, indent + 20)}
                </details>
                """
            else:
                html += f"""
                <div style="margin-left: {indent}px; padding: 5px;">
                    <span style="color: #666;">Item {i}:</span> 
                    <span style="color: #333;">{item}</span>
                </div>
                """
        return html
    else:
        return f"<div style='margin-left: {indent}px'>{data}</div>"

def display_grades_json(grades_data):
    tabs = st.tabs(["Tree View", "Raw JSON"])
    
    with tabs[0]:
        # Custom CSS for the tree view
        st.markdown("""
        <style>
        details {
            border: 1px solid #eee;
            border-radius: 4px;
            padding: 5px;
            margin: 5px 0;
        }
        details > summary {
            background-color: #f8f9fa;
            border-radius: 4px;
            font-family: monospace;
        }
        details > div {
            margin: 10px 0;
            font-family: monospace;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Convert and display as HTML tree
        tree_html = convert_to_html_tree(grades_data)
        st.markdown(tree_html, unsafe_allow_html=True)
    
    with tabs[1]:
        st.json(grades_data)

def main():
    st.set_page_config(
        page_title="Schoology Grades JSON Viewer",
        page_icon="📊",
        layout="wide"
    )
    
    st.title('Schoology Grades - JSON View')
    
    if st.sidebar.button('🔄 Refresh Data'):
        st.rerun()
    
    grades_data = get_latest_grades()
    if not grades_data:
        st.error('No recent grades data available')
        return
    
    with st.sidebar.expander("📖 View Options", expanded=False):
        st.write("""
        - Tree View provides collapsible JSON structure
        - Click on arrows to expand/collapse sections
        - Raw view allows for easy copying of data
        - Use the refresh button to get latest data
        """)
    
    display_grades_json(grades_data)

if __name__ == "__main__":
    main()