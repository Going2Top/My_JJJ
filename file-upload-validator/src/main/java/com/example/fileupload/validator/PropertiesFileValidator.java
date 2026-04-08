package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Properties;

/**
 * Properties 文件校验器：
 * 使用 Java 原生 Properties.load() 解析，确保格式合法（key=value 或 key:value）
 * 同时要求至少包含一个有效键值对
 */
public class PropertiesFileValidator implements FileValidator {

    @Override
    public ValidationResult validate(byte[] content, String filename) {
        if (content == null || content.length == 0) {
            return ValidationResult.failure("properties 文件内容不能为空");
        }
        Properties props = new Properties();
        try (InputStreamReader reader = new InputStreamReader(
                new ByteArrayInputStream(content), StandardCharsets.UTF_8)) {
            props.load(reader);
        } catch (IOException e) {
            return ValidationResult.failure("properties 文件格式非法: " + e.getMessage());
        }
        if (props.isEmpty()) {
            return ValidationResult.failure("properties 文件不包含任何键值对");
        }
        return ValidationResult.success();
    }

    @Override
    public String getSupportedExtension() {
        return "properties";
    }
}
