package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("SqlFileValidator 测试")
class SqlFileValidatorTest {

    private SqlFileValidator validator;

    @BeforeEach
    void setUp() {
        validator = new SqlFileValidator();
    }

    @Test
    @DisplayName("SELECT 语句 -> 校验通过")
    void validSelectSql() {
        String sql = "SELECT id, name FROM users WHERE status = 1;";
        ValidationResult result = validator.validate(sql.getBytes(StandardCharsets.UTF_8), "query.sql");
        assertThat(result.isValid()).isTrue();
    }

    @Test
    @DisplayName("INSERT + CREATE 混合 -> 校验通过")
    void validDdlAndDml() {
        String sql = "CREATE TABLE orders (id INT, amount DECIMAL);\n"
                   + "INSERT INTO orders VALUES (1, 99.9);";
        ValidationResult result = validator.validate(sql.getBytes(StandardCharsets.UTF_8), "init.sql");
        assertThat(result.isValid()).isTrue();
    }

    @Test
    @DisplayName("仅有注释 -> 校验失败")
    void onlyComments() {
        String sql = "-- This is a comment\n/* block comment */";
        ValidationResult result = validator.validate(sql.getBytes(StandardCharsets.UTF_8), "comment.sql");
        assertThat(result.isValid()).isFalse();
        assertThat(result.getMessage()).contains("关键字");
    }

    @Test
    @DisplayName("普通文本伪装成 sql -> 校验失败")
    void plainTextMasqueradingAsSql() {
        String content = "This is just plain text without any sql keywords.";
        ValidationResult result = validator.validate(content.getBytes(StandardCharsets.UTF_8), "fake.sql");
        assertThat(result.isValid()).isFalse();
    }

    @Test
    @DisplayName("空文件 -> 校验失败")
    void emptyContent() {
        ValidationResult result = validator.validate(new byte[0], "empty.sql");
        assertThat(result.isValid()).isFalse();
    }
}
