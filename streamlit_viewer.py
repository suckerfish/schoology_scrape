import streamlit as st
st.set_page_config(layout="centered")
st.markdown("""
    <style>
        .block-container {
            max-width: 1000px;  # Default is around 730px
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)
from dynamodb_manager import DynamoDBManager
from datetime import datetime, timedelta
import pandas as pd
from deepdiff import DeepDiff

def get_all_snapshots():
    db = DynamoDBManager()
    response = db.table.scan(
        ProjectionExpression='#date, #data',
        ExpressionAttributeNames={
            '#date': 'Date',
            '#data': 'Data'
        }
    )
    items = response.get('Items', [])
    if not items:
        return []
    
    # Sort items by date, newest first
    return sorted(items, key=lambda x: x['Date'], reverse=True)

def format_snapshot_label(snapshot):
    # Convert ISO format to datetime
    date = datetime.fromisoformat(snapshot['Date'])
    # Format as "Feb 15, 2024 at 14:30"
    return date.strftime('%b %d, %Y at %H:%M')

def display_grades_tree(grades_data):
    # Add custom CSS to style nested expanders
    st.markdown("""
        <style>
        .streamlit-expanderHeader {
            font-weight: bold;
            background-color: #f0f2f6;
        }
        .stDataFrame {
            width: 100% !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    for course_name, course_data in grades_data.items():
        with st.expander(f"{course_name} ({course_data['course_grade']})"):
            # Sort periods by name, which will put T1 before T2
            sorted_periods = sorted(course_data['periods'].items())
            
            # Create tabs for each period
            period_tabs = st.tabs([f"{period_name} - {period_data['period_grade']}" 
                                 for period_name, period_data in sorted_periods])
            
            # Fill each tab with its content
            for tab, (period_name, period_data) in zip(period_tabs, sorted_periods):
                with tab:
                    for category_name, category_data in period_data['categories'].items():
                        st.write(f"**{category_name} - {category_data['category_grade']}**")
                        
                        # Create a DataFrame for assignments in this category
                        assignments = category_data['assignments']
                        if assignments:
                            df = pd.DataFrame(
                                [[a['title'], a['grade']] for a in assignments],
                                columns=['Assignment', 'Grade']
                            )
                            st.table(df.set_index('Assignment'))
                    st.divider()

def display_grade_changes(current_data, previous_data):
    st.header("Changes from Previous Snapshot")
    
    if not previous_data:
        st.info("No previous snapshot available for comparison")
        return
    
    changes_found = False
    
    # Compare course by course
    for course_name, current_course in current_data.items():
        course_changes = []
        
        # Check course grade changes
        if course_name in previous_data:
            prev_course = previous_data[course_name]
            if current_course['course_grade'] != prev_course['course_grade']:
                course_changes.append(f"Course grade changed from {prev_course['course_grade']} to {current_course['course_grade']}")
            
            # Check each period
            for period_name, current_period in current_course['periods'].items():
                if period_name in prev_course['periods']:
                    prev_period = prev_course['periods'][period_name]
                    
                    # Check period grade changes
                    if current_period['period_grade'] != prev_period['period_grade']:
                        course_changes.append(f"{period_name} grade changed from {prev_period['period_grade']} to {current_period['period_grade']}")
                    
                    # Check assignments in each category
                    for cat_name, current_cat in current_period['categories'].items():
                        if cat_name in prev_course['periods'][period_name]['categories']:
                            prev_cat = prev_course['periods'][period_name]['categories'][cat_name]
                            
                            # Create dictionaries of assignments for easy comparison
                            current_assignments = {a['title']: {'grade': a['grade'], 'comment': a.get('comment', '')} 
                                                for a in current_cat['assignments']}
                            prev_assignments = {a['title']: {'grade': a['grade'], 'comment': a.get('comment', '')} 
                                             for a in prev_cat['assignments']}
                            
                            # Check for new or changed assignments
                            for title, current_info in current_assignments.items():
                                if title not in prev_assignments:
                                    course_changes.append(f"New assignment in {cat_name}: {title} ({current_info['grade']})")
                                else:
                                    prev_info = prev_assignments[title]
                                    if current_info['grade'] != prev_info['grade']:
                                        course_changes.append(f"In {cat_name}, {title} grade changed from {prev_info['grade']} to {current_info['grade']}")
                                    if current_info['comment'] != prev_info['comment']:
                                        if current_info['comment']:  # Only show if there's a new comment
                                            course_changes.append(f"New comment on {title}: {current_info['comment']}")
        else:
            # New course added
            course_changes.append("New course added")
        
        # Display changes for this course if any were found
        if course_changes:
            changes_found = True
            with st.expander(f"Changes in {course_name}"):
                for change in course_changes:
                    st.write(change)
    
    if not changes_found:
        st.success("No changes detected")

def main():
    st.title('Schoology Grades')
    
    # Get all snapshots
    snapshots = get_all_snapshots()
    if not snapshots:
        st.error('No grades data available')
        return
    
    # Create list of snapshot labels
    snapshot_labels = [format_snapshot_label(snapshot) for snapshot in snapshots]
    
    # Add snapshot selector with the most recent as default
    selected_label = st.selectbox(
        'Select Snapshot',
        snapshot_labels,
        index=0  # Default to most recent
    )
    
    # Find the selected snapshot
    selected_index = snapshot_labels.index(selected_label)
    selected_snapshot = snapshots[selected_index]
    
    # Display timestamp of selected snapshot
    st.caption(f"Viewing grades as of {selected_label}")
    
    # Display the grades for the selected snapshot
    display_grades_tree(selected_snapshot['Data'])
    
    # Get previous snapshot for diff
    previous_snapshot = snapshots[selected_index + 1] if selected_index + 1 < len(snapshots) else None
    
    if previous_snapshot:
        st.divider()
        display_grade_changes(selected_snapshot['Data'], previous_snapshot['Data'])

if __name__ == "__main__":
    main()