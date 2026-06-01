#!/usr/bin/env python3
"""
Backfill workspace_id for existing resources after migration.

This script reads app->workspace mappings from the controller database
and updates the resources database with the correct workspace_id values.

Usage:
    python backfill_workspace.py --controller-db <url> --resources-db <url>
"""
import argparse
import psycopg2
import sys


def main():
    parser = argparse.ArgumentParser(description='Backfill workspace_id in resources database')
    parser.add_argument('--controller-db', required=True, help='Controller database URL')
    parser.add_argument('--resources-db', required=True, help='Resources database URL')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    
    args = parser.parse_args()
    
    try:
        # Connect to controller database
        print(f"Connecting to controller database: {args.controller_db}")
        controller_conn = psycopg2.connect(args.controller_db)
        controller_cursor = controller_conn.cursor()
        
        # Get app_id -> workspace_id mapping
        controller_cursor.execute("SELECT id, workspace_id FROM api_app")
        app_workspace_map = {row[0]: row[1] for row in controller_cursor.fetchall()}
        print(f"Found {len(app_workspace_map)} apps in controller database")
        
        controller_cursor.close()
        controller_conn.close()
        
        # Connect to resources database
        print(f"Connecting to resources database: {args.resources_db}")
        resources_conn = psycopg2.connect(args.resources_db)
        resources_cursor = resources_conn.cursor()
        
        # Get resources that need workspace_id
        resources_cursor.execute("SELECT uuid, app_id FROM api_resource WHERE workspace_id IS NULL OR workspace_id = ''")
        resources_to_update = resources_cursor.fetchall()
        print(f"Found {len(resources_to_update)} resources to update")
        
        if args.dry_run:
            print("\nDry run - would update:")
            for uuid, app_id in resources_to_update:
                workspace_id = app_workspace_map.get(app_id)
                if workspace_id:
                    print(f"  Resource {uuid} (app: {app_id}) -> workspace: {workspace_id}")
                else:
                    print(f"  Resource {uuid} (app: {app_id}) -> NO WORKSPACE FOUND")
        else:
            # Update resources
            updated = 0
            not_found = 0
            for uuid, app_id in resources_to_update:
                workspace_id = app_workspace_map.get(app_id)
                if workspace_id:
                    resources_cursor.execute(
                        "UPDATE api_resource SET workspace_id = %s WHERE uuid = %s",
                        (workspace_id, uuid)
                    )
                    updated += 1
                else:
                    print(f"Warning: No workspace found for app {app_id} (resource {uuid})")
                    not_found += 1
            
            resources_conn.commit()
            print(f"\nUpdated {updated} resources")
            if not_found > 0:
                print(f"Warning: {not_found} resources could not be updated (no workspace found)")
        
        resources_cursor.close()
        resources_conn.close()
        
        print("\nBackfill complete!")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
