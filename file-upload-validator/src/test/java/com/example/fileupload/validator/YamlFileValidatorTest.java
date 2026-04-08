package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("YamlFileValidator 测试")
class YamlFileValidatorTest {

    private YamlFileValidator validator;

    @BeforeEach
    void setUp() {
        validator = new YamlFileValidator();
    }

    @Test
    @DisplayName("合法 YAML -> 校验通过")
    void validYaml() {
        String yaml = "server:\n  port: 8080\nspring:\n  datasource:\n    url: jdbc:mysql://localhost/db\n";
        ValidationResult result = validator.validate(yaml.getBytes(StandardCharsets.UTF_8), "config.yaml");
        assertThat(result.isValid()).isTrue();
    }

    @Test
    @DisplayName("简单键值 YAML -> 校验通过")
    void simpleKeyValueYaml() {
        String yaml = "name: John\nage: 30";
        ValidationResult result = validator.validate(yaml.getBytes(StandardCharsets.UTF_8), "person.yaml");
        assertThat(result.isValid()).isTrue();
    }

    @Test
    @DisplayName("格式非法的 YAML -> 校验失败")
    void invalidYaml() {
        String yaml = "key: value\n  bad_indent: [unclosed";
        ValidationResult result = validator.validate(yaml.getBytes(StandardCharsets.UTF_8), "invalid.yaml");
        assertThat(result.isValid()).isFalse();
        assertThat(result.getMessage()).contains("格式非法");
    }

    @Test
    @DisplayName("仅有注释 -> 校验失败（解析结果为空）")
    void onlyComments() {
        String yaml = "# Just a comment\n# Another comment";
        ValidationResult result = validator.validate(yaml.getBytes(StandardCharsets.UTF_8), "comments.yaml");
        assertThat(result.isValid()).isFalse();
        assertThat(result.getMessage()).contains("为空");
    }

    @Test
    @DisplayName("空文件 -> 校验失败")
    void emptyContent() {
        ValidationResult result = validator.validate(new byte[0], "empty.yaml");
        assertThat(result.isValid()).isFalse();
    }
}
