package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("TxtFileValidator 测试")
class TxtFileValidatorTest {

    private TxtFileValidator validator;

    @BeforeEach
    void setUp() {
        validator = new TxtFileValidator();
    }

    @Test
    @DisplayName("合法 UTF-8 文本 -> 校验通过")
    void validUtf8Text() {
        byte[] content = "Hello, 世界！\nThis is a test.".getBytes(StandardCharsets.UTF_8);
        ValidationResult result = validator.validate(content, "test.txt");
        assertThat(result.isValid()).isTrue();
    }

    @Test
    @DisplayName("空内容 -> 校验失败")
    void emptyContent() {
        ValidationResult result = validator.validate(new byte[0], "empty.txt");
        assertThat(result.isValid()).isFalse();
        assertThat(result.getMessage()).contains("不能为空");
    }

    @Test
    @DisplayName("非文本二进制数据 -> 校验失败")
    void binaryContent() {
        // 构造无效 UTF-8 字节序列
        byte[] content = {(byte) 0xFF, (byte) 0xFE, (byte) 0x00, (byte) 0x01, (byte) 0x80, (byte) 0x81};
        ValidationResult result = validator.validate(content, "binary.txt");
        assertThat(result.isValid()).isFalse();
    }
}
