CREATE TABLE `llm_keys` (
	`id` text PRIMARY KEY NOT NULL,
	`enterprise_id` text NOT NULL,
	`provider` text NOT NULL,
	`encrypted_key` text NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`enterprise_id`) REFERENCES `enterprises`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `operation_logs` (
	`id` text PRIMARY KEY NOT NULL,
	`enterprise_id` text NOT NULL,
	`user_id` text NOT NULL,
	`action` text NOT NULL,
	`resource_type` text NOT NULL,
	`resource_id` text,
	`details` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`enterprise_id`) REFERENCES `enterprises`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);
