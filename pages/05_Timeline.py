import streamlit as st
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from utils.change_parser import (
    parse_detailed_message,
    load_snapshot_for_timestamp,
    calculate_grade_delta,
    get_grade_style
)

st.set_page_config(layout="wide", page_title="Change Timeline")

def load_change_history(days=30):
    """Load recent changes from grade_changes.log"""
    log_file = Path("logs/grade_changes.log")
    if not log_file.exists():
        return []

    changes = []
    try:
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    changes.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        st.error(f"Error reading change log: {e}")
        return []

    # Sort by timestamp, newest first
    changes.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # Return only the requested number of days
    if days and days > 0:
        cutoff = datetime.now()
        cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)
        changes = [c for c in changes if datetime.fromisoformat(c['timestamp']) >= cutoff]

    return changes

def format_timestamp(timestamp_str):
    """Format ISO timestamp into readable format"""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%b %d, %Y at %I:%M %p")
    except:
        return timestamp_str

def get_priority_emoji(priority):
    """Get emoji based on priority level"""
    priority_map = {
        'high': '🔴',
        'normal': '🟡',
        'low': '🟢'
    }
    return priority_map.get(priority, '⚪')

def get_change_type_emoji(metadata):
    """Get emoji based on change type"""
    if metadata.get('has_grade_changes'):
        return '📊'
    elif metadata.get('has_new_assignments'):
        return '📝'
    elif metadata.get('has_removed_items'):
        return '🗑️'
    else:
        return '🔄'


def display_change_card(entry):
    """Display a single change entry as a card"""
    timestamp = entry.get('timestamp', '')
    change_count = entry.get('change_count', 0)
    priority = entry.get('priority', 'low')
    metadata = entry.get('metadata', {})
    formatted_message = entry.get('formatted_message', '')

    # Load snapshot data for assignment name lookup
    snapshot_data = load_snapshot_for_timestamp(timestamp)

    # Parse the detailed message with snapshot data
    parsed = parse_detailed_message(formatted_message, snapshot_data)

    # Create card container
    with st.container(border=True):
        # Header row with timestamp and badges
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"### {format_timestamp(timestamp)}")

        with col2:
            if change_count > 0:
                st.markdown(f"**{change_count} change{'s' if change_count != 1 else ''}**")

        with col3:
            st.markdown(f"{get_priority_emoji(priority)} {get_change_type_emoji(metadata)}")

        # Summary section
        if parsed:
            st.markdown(f"**{parsed['summary']}**")

            # Show detailed changes in an expander
            with st.expander("📋 Show detailed changes"):
                if parsed['parsed_changes']:
                    # Create DataFrame from parsed changes
                    df = pd.DataFrame(parsed['parsed_changes'])

                    # Select and rename columns for display - now includes Assignment
                    display_df = df[['course', 'category', 'assignment', 'field', 'old_value', 'new_value']].copy()
                    display_df.columns = ['Course', 'Category', 'Assignment', 'Type', 'Old Value', 'New Value']

                    # Clean up empty categories
                    display_df['Category'] = display_df['Category'].replace('', '—')

                    # Add delta column for grade changes
                    if 'delta' in df.columns:
                        display_df['Change'] = df['delta'].apply(
                            lambda d: d['display'] if isinstance(d, dict) and d else '—'
                        )

                    # Apply styling to grade rows
                    def style_row(row):
                        styles = get_grade_style(row['Old Value'], row['New Value'], row['Type'])
                        return [f"background-color: {styles.get('background-color', '')}" for _ in row]

                    # Display as a styled dataframe
                    st.dataframe(
                        display_df,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            'Course': st.column_config.TextColumn(width="medium"),
                            'Category': st.column_config.TextColumn(width="small"),
                            'Assignment': st.column_config.TextColumn(width="medium"),
                            'Type': st.column_config.TextColumn(width="small"),
                            'Old Value': st.column_config.TextColumn(width="large"),
                            'New Value': st.column_config.TextColumn(width="large"),
                            'Change': st.column_config.TextColumn(width="small") if 'Change' in display_df.columns else None,
                        }
                    )
                else:
                    # Fallback to raw display if parsing failed
                    for change in parsed['raw_changes']:
                        st.markdown(f"• {change}")
        else:
            st.info("No changes detected")

        # Show notification status
        notification_results = entry.get('notification_results', {})
        if notification_results:
            st.caption(f"📤 Sent via: {', '.join([k for k, v in notification_results.items() if v])}")

def group_by_date(changes):
    """Group changes by date"""
    grouped = {}
    for entry in changes:
        timestamp = entry.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(timestamp)
            date_key = dt.strftime("%Y-%m-%d")
            if date_key not in grouped:
                grouped[date_key] = []
            grouped[date_key].append(entry)
        except:
            continue

    return grouped

def main():
    st.title('📅 Change Timeline')
    st.caption("Daily summary of grade changes and updates")

    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        days_filter = st.slider("Days to show", 7, 90, 30)

        st.divider()

        show_no_changes = st.checkbox("Show 'no changes' entries", value=False)
        group_by_day = st.checkbox("Group by day", value=True)

    # Load changes
    changes = load_change_history(days=days_filter)

    if not changes:
        st.info("No changes found in the selected time period.")
        return

    # Filter out "no changes" entries if requested
    if not show_no_changes:
        changes = [c for c in changes if c.get('change_count', 0) > 0]

    # Display stats
    total_changes = len(changes)
    total_grade_changes = sum(1 for c in changes if c.get('metadata', {}).get('has_grade_changes'))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Snapshots", total_changes)
    with col2:
        st.metric("Grade Changes", total_grade_changes)
    with col3:
        avg_changes = sum(c.get('change_count', 0) for c in changes) / total_changes if total_changes > 0 else 0
        st.metric("Avg Changes/Day", f"{avg_changes:.1f}")

    st.divider()

    # Display changes
    if group_by_day:
        grouped = group_by_date(changes)

        for date_key in sorted(grouped.keys(), reverse=True):
            day_changes = grouped[date_key]
            dt = datetime.fromisoformat(date_key)

            # Date header
            st.subheader(dt.strftime("%A, %B %d, %Y"))

            # Show each change for this day
            for entry in sorted(day_changes, key=lambda x: x.get('timestamp', ''), reverse=True):
                display_change_card(entry)

            st.markdown("---")
    else:
        # Show all changes in chronological order
        for entry in changes:
            display_change_card(entry)

if __name__ == "__main__":
    main()
