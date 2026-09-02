TRUNCATE TABLE
    users,
    user_token_caches,
    workspaces,
    workspace_conversations,
    followups,
    uploads,
    applications,
    applications_snapshot,
    applications_raw_data,
    application_analysis,
    application_mail_config,
    application_meetings,
    application_comments,
    comparison_logs,
    comparison_changes,
    master_control
RESTART IDENTITY CASCADE;