CREATE TABLE `agent_templates` (
	`id` text PRIMARY KEY NOT NULL,
	`enterprise_id` text,
	`platform` text NOT NULL,
	`name` text NOT NULL,
	`profile_config` text NOT NULL,
	`is_public` integer DEFAULT 0 NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `enterprises` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`contact_phone` text,
	`status` text DEFAULT 'active' NOT NULL,
	`plan_type` text DEFAULT 'basic' NOT NULL,
	`sim_quota` integer DEFAULT 0 NOT NULL,
	`quota_expires` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `llm_usage` (
	`id` text PRIMARY KEY NOT NULL,
	`simulation_id` text NOT NULL,
	`enterprise_id` text NOT NULL,
	`provider` text,
	`model` text,
	`input_tokens` integer,
	`output_tokens` integer,
	`cost_yuan` real,
	`agent_tier` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`simulation_id`) REFERENCES `simulations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`enterprise_id`) REFERENCES `enterprises`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `orders` (
	`id` text PRIMARY KEY NOT NULL,
	`enterprise_id` text NOT NULL,
	`plan_type` text NOT NULL,
	`amount` integer NOT NULL,
	`sim_quota` integer NOT NULL,
	`duration_days` integer NOT NULL,
	`status` text DEFAULT 'pending' NOT NULL,
	`paid_at` text,
	`notes` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`enterprise_id`) REFERENCES `enterprises`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `reports` (
	`id` text PRIMARY KEY NOT NULL,
	`simulation_id` text NOT NULL,
	`enterprise_id` text NOT NULL,
	`title` text NOT NULL,
	`summary` text,
	`dashboard_data` text,
	`pdf_url` text,
	`raw_data_url` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`simulation_id`) REFERENCES `simulations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`enterprise_id`) REFERENCES `enterprises`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `simulation_templates` (
	`id` text PRIMARY KEY NOT NULL,
	`enterprise_id` text,
	`name` text NOT NULL,
	`type` text NOT NULL,
	`platform` text NOT NULL,
	`config` text NOT NULL,
	`is_public` integer DEFAULT 0 NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `simulations` (
	`id` text PRIMARY KEY NOT NULL,
	`enterprise_id` text NOT NULL,
	`user_id` text NOT NULL,
	`name` text NOT NULL,
	`type` text NOT NULL,
	`platform` text NOT NULL,
	`config` text NOT NULL,
	`status` text DEFAULT 'pending' NOT NULL,
	`progress` integer DEFAULT 0 NOT NULL,
	`agent_count` integer,
	`time_steps` integer,
	`llm_model` text,
	`started_at` text,
	`completed_at` text,
	`error_message` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`enterprise_id`) REFERENCES `enterprises`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `sms_codes` (
	`id` text PRIMARY KEY NOT NULL,
	`phone` text NOT NULL,
	`code` text NOT NULL,
	`expires_at` text NOT NULL,
	`used` integer DEFAULT 0 NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `users` (
	`id` text PRIMARY KEY NOT NULL,
	`enterprise_id` text NOT NULL,
	`phone` text NOT NULL,
	`name` text,
	`role` text DEFAULT 'user' NOT NULL,
	`last_login_at` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`enterprise_id`) REFERENCES `enterprises`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `users_phone_unique` ON `users` (`phone`);