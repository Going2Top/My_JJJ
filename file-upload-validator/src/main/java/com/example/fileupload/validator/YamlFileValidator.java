package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.error.YAMLException;

import java.io.ByteArrayInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

/**
 * YAML 文件校验器：
 * 使用 SnakeYAML 解析，确保是合法的 YAML 格式，且内容不为 null
 */
public class YamlFileValidator implements FileValidator {

    @Override
    public ValidationResult validate(byte[] content, String filename) {
        if (content == null || content.length == 0) {
            return ValidationResult.failure("yaml 文件内容不能为空");
        }

        Yaml yaml = new Yaml();
        try (InputStreamReader reader = new InputStreamReader(
                new ByteArrayInputStream(content), StandardCharsets.UTF_8)) {
            Object parsed = yaml.load(reader);
            if (parsed == null) {
                return ValidationResult.failure("yaml 文件解析结果为空（仅包含注释或空白）");
            }
            return ValidationResult.success();
        } catch (YAMLException e) {
            return ValidationResult.failure("yaml 文件格式非法: " + e.getMessage());
        } catch (Exception e) {
            return ValidationResult.failure("yaml 文件读取失败: " + e.getMessage());
        }
    }

    @Override
    public String getSupportedExtension() {
        return "yaml";
    }
}
