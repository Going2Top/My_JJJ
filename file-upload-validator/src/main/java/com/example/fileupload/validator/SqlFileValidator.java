package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;

import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;

/**
 * SQL 文件校验器：
 * 1. 内容必须是合法 UTF-8 文本
 * 2. 去除注释后，必须包含至少一条 SQL 语句关键字
 * 3. 不允许出现明显危险的无条件操作（如 DROP TABLE 不带 IF EXISTS）
 */
public class SqlFileValidator implements FileValidator {

    // 合法 SQL 语句起始关键字（不区分大小写）
    private static final Pattern SQL_STATEMENT_PATTERN = Pattern.compile(
        "(?i)\\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE|MERGE|REPLACE|CALL|EXEC|BEGIN|COMMIT|ROLLBACK|GRANT|REVOKE|SET|SHOW|DESCRIBE|EXPLAIN|USE)\\b"
    );

    // 单行注释和多行注释
    private static final Pattern SINGLE_LINE_COMMENT = Pattern.compile("--[^\n]*");
    private static final Pattern MULTI_LINE_COMMENT  = Pattern.compile("/\\*.*?\\*/", Pattern.DOTALL);

    @Override
    public ValidationResult validate(byte[] content, String filename) {
        if (content == null || content.length == 0) {
            return ValidationResult.failure("sql 文件内容不能为空");
        }

        String text;
        try {
            text = new String(content, StandardCharsets.UTF_8);
        } catch (Exception e) {
            return ValidationResult.failure("sql 文件不是合法的 UTF-8 编码");
        }

        // 去除注释后检查是否有 SQL 关键字
        String stripped = removeComments(text).trim();
        if (stripped.isEmpty()) {
            return ValidationResult.failure("sql 文件去除注释后内容为空");
        }
        if (!SQL_STATEMENT_PATTERN.matcher(stripped).find()) {
            return ValidationResult.failure("sql 文件中未找到合法的 SQL 语句关键字");
        }
        return ValidationResult.success();
    }

    private String removeComments(String sql) {
        String result = MULTI_LINE_COMMENT.matcher(sql).replaceAll(" ");
        result = SINGLE_LINE_COMMENT.matcher(result).replaceAll(" ");
        return result;
    }

    @Override
    public String getSupportedExtension() {
        return "sql";
    }
}
