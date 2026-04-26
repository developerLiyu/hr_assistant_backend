ALTER TABLE `hr_assistant`.`candidate_comparison`
CHANGE COLUMN `ai_analysis` `candidate_analysis` json NULL COMMENT '候选人分析' AFTER `comparison_data`,
ADD COLUMN `comparison_summary` json NULL COMMENT '对比总结' AFTER `comparison_data`,
ADD COLUMN `recommendation` json NULL COMMENT '候选人建议' AFTER `ranking`,
ADD COLUMN `hiring_advice` json NULL COMMENT '录用建议' AFTER `recommendation`;

commit;




ALTER TABLE `hr_assistant`.`candidate_comparison`
MODIFY COLUMN `comparison_summary` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '对比总结' AFTER `comparison_data`,
MODIFY COLUMN `hiring_advice` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '录用建议' AFTER `recommendation`;
commit;


