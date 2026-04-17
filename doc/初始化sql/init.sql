-- 创建数据库
CREATE DATABASE IF NOT EXISTS hr_assistant
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE hr_assistant;



-- 创建表
CREATE TABLE job_position (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    position_name VARCHAR(100) NOT NULL COMMENT '岗位名称',
    department VARCHAR(100) NOT NULL COMMENT '所属部门',
    job_description TEXT NOT NULL COMMENT '岗位职责描述',
    requirements TEXT NOT NULL COMMENT '任职要求',
    salary_range VARCHAR(50) DEFAULT NULL COMMENT '薪资范围',
    work_location VARCHAR(100) DEFAULT NULL COMMENT '工作地点',
    headcount INT DEFAULT 1 COMMENT '招聘人数',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-开放 2-暂停 3-关闭',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '软删除：0-正常 1-已删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_department (department),
    INDEX idx_status (status),
    INDEX idx_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位表';


CREATE TABLE resume (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    candidate_name VARCHAR(50) NOT NULL COMMENT '候选人姓名',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    education VARCHAR(20) DEFAULT NULL COMMENT '学历',
    school VARCHAR(100) DEFAULT NULL COMMENT '毕业院校',
    major VARCHAR(100) DEFAULT NULL COMMENT '专业',
    work_years INT DEFAULT NULL COMMENT '工作年限',
    current_company VARCHAR(100) DEFAULT NULL COMMENT '当前公司',
    current_position VARCHAR(100) DEFAULT NULL COMMENT '当前职位',
    skills JSON DEFAULT NULL COMMENT '技能标签',
    work_experience JSON DEFAULT NULL COMMENT '工作经历',
    project_experience JSON DEFAULT NULL COMMENT '项目经验',
    education_experience JSON DEFAULT NULL COMMENT '教育经历',
    resume_summary TEXT DEFAULT NULL COMMENT 'AI简历摘要',
    original_content MEDIUMTEXT DEFAULT NULL COMMENT '简历原始文本',
    file_path VARCHAR(500) NOT NULL COMMENT '文件存储路径',
    file_name VARCHAR(200) NOT NULL COMMENT '原始文件名',
    file_type VARCHAR(10) NOT NULL COMMENT '文件类型：pdf/docx/doc',
    file_size BIGINT DEFAULT NULL COMMENT '文件大小(字节)',
    milvus_id VARCHAR(100) DEFAULT NULL COMMENT 'Milvus向量ID',
    position_id BIGINT DEFAULT NULL COMMENT '关联岗位ID',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-待筛选 2-初筛通过 3-面试中 4-已录用 5-已淘汰',
    parse_status TINYINT NOT NULL DEFAULT 0 COMMENT '解析状态：0-未解析 1-解析中 2-成功 3-失败',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '软删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_position (position_id),
    INDEX idx_status (status),
    INDEX idx_education (education),
    INDEX idx_work_years (work_years),
    INDEX idx_parse_status (parse_status),
    INDEX idx_deleted (is_deleted),
    CONSTRAINT fk_resume_position FOREIGN KEY (position_id) REFERENCES job_position(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历表';


CREATE TABLE interview_question (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    position_id BIGINT DEFAULT NULL COMMENT '关联岗位ID',
    resume_id BIGINT DEFAULT NULL COMMENT '关联简历ID',
    question_type VARCHAR(20) NOT NULL COMMENT '题目类型：technical/behavioral/situational/open',
    difficulty VARCHAR(10) NOT NULL COMMENT '难度：junior/middle/senior',
    question_content TEXT NOT NULL COMMENT '题目内容',
    reference_answer TEXT DEFAULT NULL COMMENT '参考答案',
    scoring_points JSON DEFAULT NULL COMMENT '评分要点',
    source VARCHAR(50) DEFAULT NULL COMMENT '题目来源',
    is_saved TINYINT DEFAULT 0 COMMENT '是否保存到题库',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_position (position_id),
    INDEX idx_resume (resume_id),
    INDEX idx_type (question_type),
    INDEX idx_difficulty (difficulty)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试题表';


CREATE TABLE interview_recording (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    resume_id BIGINT NOT NULL COMMENT '关联简历ID',
    position_id BIGINT DEFAULT NULL COMMENT '关联岗位ID',
    file_name VARCHAR(200) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '存储路径',
    file_type VARCHAR(10) NOT NULL COMMENT '文件类型：mp3/wav/m4a',
    file_size BIGINT NOT NULL COMMENT '文件大小(字节)',
    duration INT DEFAULT NULL COMMENT '时长(秒)',
    transcript LONGTEXT DEFAULT NULL COMMENT '文字稿',
    transcript_status TINYINT NOT NULL DEFAULT 0 COMMENT '转写状态：0-未转写 1-转写中 2-已完成 3-失败',
    transcript_error VARCHAR(500) DEFAULT NULL COMMENT '转写错误信息',
    interviewer VARCHAR(50) DEFAULT NULL COMMENT '面试官',
    interview_date DATE DEFAULT NULL COMMENT '面试日期',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_resume (resume_id),
    INDEX idx_status (transcript_status),
    INDEX idx_interview_date (interview_date),
    CONSTRAINT fk_recording_resume FOREIGN KEY (resume_id) REFERENCES resume(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试录音表';


CREATE TABLE interview_summary (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    recording_id BIGINT NOT NULL COMMENT '关联录音ID',
    resume_id BIGINT NOT NULL COMMENT '关联简历ID',
    summary_overview TEXT NOT NULL COMMENT '面试概要',
    key_qa JSON DEFAULT NULL COMMENT '核心问答',
    technical_skills JSON DEFAULT NULL COMMENT '技术能力标签',
    soft_skills JSON DEFAULT NULL COMMENT '软技能标签',
    highlights TEXT DEFAULT NULL COMMENT '亮点',
    concerns TEXT DEFAULT NULL COMMENT '疑虑点',
    candidate_questions TEXT DEFAULT NULL COMMENT '候选人提问',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_recording (recording_id),
    INDEX idx_resume (resume_id),
    CONSTRAINT fk_summary_recording FOREIGN KEY (recording_id) REFERENCES interview_recording(id) ON DELETE CASCADE,
    CONSTRAINT fk_summary_resume FOREIGN KEY (resume_id) REFERENCES resume(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试摘要表';


CREATE TABLE interview_evaluation (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    resume_id BIGINT NOT NULL COMMENT '关联简历ID',
    recording_id BIGINT DEFAULT NULL COMMENT '关联录音ID',
    summary_id BIGINT DEFAULT NULL COMMENT '关联摘要ID',
    professional_score INT NOT NULL COMMENT '专业能力评分',
    professional_comment VARCHAR(200) DEFAULT NULL COMMENT '专业能力评语',
    logic_score INT NOT NULL COMMENT '逻辑思维评分',
    logic_comment VARCHAR(200) DEFAULT NULL COMMENT '逻辑思维评语',
    communication_score INT NOT NULL COMMENT '沟通表达评分',
    communication_comment VARCHAR(200) DEFAULT NULL COMMENT '沟通表达评语',
    learning_score INT NOT NULL COMMENT '学习能力评分',
    learning_comment VARCHAR(200) DEFAULT NULL COMMENT '学习能力评语',
    teamwork_score INT NOT NULL COMMENT '团队协作评分',
    teamwork_comment VARCHAR(200) DEFAULT NULL COMMENT '团队协作评语',
    culture_score INT NOT NULL COMMENT '文化匹配评分',
    culture_comment VARCHAR(200) DEFAULT NULL COMMENT '文化匹配评语',
    total_score DECIMAL(5,2) NOT NULL COMMENT '综合得分',
    recommendation VARCHAR(20) NOT NULL COMMENT '推荐等级：强烈推荐/推荐/一般/不推荐',
    ai_comment TEXT DEFAULT NULL COMMENT 'AI综合评语',
    key_strengths JSON DEFAULT NULL COMMENT '核心优势',
    improvement_areas JSON DEFAULT NULL COMMENT '待提升领域',
    hiring_suggestion TEXT DEFAULT NULL COMMENT '录用建议',
    hr_comment TEXT DEFAULT NULL COMMENT 'HR补充评价',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_resume (resume_id),
    INDEX idx_total_score (total_score),
    INDEX idx_recommendation (recommendation),
    CONSTRAINT fk_evaluation_resume FOREIGN KEY (resume_id) REFERENCES resume(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试评价表';


CREATE TABLE candidate_comparison (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    position_id BIGINT NOT NULL COMMENT '岗位ID',
    resume_ids JSON NOT NULL COMMENT '简历ID列表',
    comparison_data JSON DEFAULT NULL COMMENT '对比数据快照',
    ai_analysis JSON DEFAULT NULL COMMENT 'AI分析结果',
    ranking JSON DEFAULT NULL COMMENT '排名结果',
    created_by BIGINT DEFAULT NULL COMMENT '创建人ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_position (position_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='候选人对比表';


CREATE TABLE sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    password VARCHAR(100) NOT NULL COMMENT '密码(加密)',
    real_name VARCHAR(50) DEFAULT NULL COMMENT '真实姓名',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    avatar VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-正常 0-禁用',
    last_login_time DATETIME DEFAULT NULL COMMENT '最后登录时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';






-- 插入初始化数据
-- 插入默认管理员账号 (密码: admin123，使用bcrypt加密)
INSERT INTO sys_user (username, password, real_name) VALUES
('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EH', 'HR管理员');

-- 插入测试数据（可选）
INSERT INTO job_position (position_name, department, job_description, requirements, salary_range, work_location, headcount) VALUES
('高级Java开发工程师', '技术部', '负责公司核心系统的设计与开发，参与技术方案评审...', '1. 本科及以上学历\n2. 5年以上Java开发经验...', '25k-40k', '北京', 2),
('产品经理', '产品部', '负责产品规划、需求分析、原型设计...', '1. 本科及以上学历\n2. 3年以上产品经验...', '30k-50k', '北京', 1);


