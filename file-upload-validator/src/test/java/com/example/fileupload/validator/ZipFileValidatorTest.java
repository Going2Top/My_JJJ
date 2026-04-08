package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("ZipFileValidator 测试")
class ZipFileValidatorTest {

    private ZipFileValidator validator;

    @BeforeEach
    void setUp() {
        validator = new ZipFileValidator();
    }

    @Test
    @DisplayName("合法 ZIP 文件 -> 校验通过")
    void validZip() throws IOException {
        byte[] zipBytes = buildZip("hello.txt", "Hello World");
        ValidationResult result = validator.validate(zipBytes, "archive.zip");
        assertThat(result.isValid()).isTrue();
    }

    @Test
    @DisplayName("普通文本伪装成 zip -> 校验失败（魔数不匹配）")
    void textMasqueradingAsZip() {
        byte[] content = "This is not a zip file".getBytes();
        ValidationResult result = validator.validate(content, "fake.zip");
        assertThat(result.isValid()).isFalse();
        assertThat(result.getMessage()).contains("魔数");
    }

    @Test
    @DisplayName("空内容 -> 校验失败")
    void emptyContent() {
        ValidationResult result = validator.validate(new byte[0], "empty.zip");
        assertThat(result.isValid()).isFalse();
    }

    @Test
    @DisplayName("内容过短（不足4字节）-> 校验失败")
    void tooShortContent() {
        ValidationResult result = validator.validate(new byte[]{0x50, 0x4B}, "short.zip");
        assertThat(result.isValid()).isFalse();
    }

    private byte[] buildZip(String entryName, String entryContent) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos)) {
            zos.putNextEntry(new ZipEntry(entryName));
            zos.write(entryContent.getBytes());
            zos.closeEntry();
        }
        return baos.toByteArray();
    }
}
