package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("PropertiesFileValidator 测试")
class PropertiesFileValidatorTest {

    private PropertiesFileValidator validator;

    @BeforeEach
    void setUp() {
        validator = new PropertiesFileValidator();
    }

    @Test
    @DisplayName("合法 key=value 格式 -> 校验通过")
    void validProperties() {
        String content = "server.port=8080\nspring.datasource.url=jdbc:mysql://localhost/db\n# comment\n";
        ValidationResult result = validator.validate(content.getBytes(StandardCharsets.UTF_8), "app.properties");
        assertThat(result.isValid()).isTrue();
    }

    @Test
    @DisplayName("冒号分隔格式 -> 校验通过")
    void colonSeparatedProperties() {
        String content = "key1: value1\nkey2: value2";
        ValidationResult result = validator.validate(content.getBytes(StandardCharsets.UTF_8), "config.properties");
        assertThat(result.isValid()).isTrue();
    }

    @Test
    @DisplayName("仅有注释的文件 -> 校验失败（无键值对）")
    void onlyComments() {
        String content = "# This is just a comment\n! Another comment";
        ValidationResult result = validator.validate(content.getBytes(StandardCharsets.UTF_8), "comments.properties");
        assertThat(result.isValid()).isFalse();
        assertThat(result.getMessage()).contains("键值对");
    }

    @Test
    @DisplayName("空文件 -> 校验失败")
    void emptyContent() {
        ValidationResult result = validator.validate(new byte[0], "empty.properties");
        assertThat(result.isValid()).isFalse();
    }
}
