package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;

import java.io.ByteArrayInputStream;
import java.util.zip.ZipInputStream;

/**
 * ZIP 文件校验器：
 * 1. 检查魔数（PK\x03\x04）
 * 2. 用 ZipInputStream 解析，确保至少有一个有效条目
 */
public class ZipFileValidator implements FileValidator {

    // ZIP 文件魔数：PK (0x50 0x4B 0x03 0x04)
    private static final byte[] ZIP_MAGIC = {0x50, 0x4B, 0x03, 0x04};

    @Override
    public ValidationResult validate(byte[] content, String filename) {
        if (content == null || content.length < 4) {
            return ValidationResult.failure("zip 文件内容过短或为空");
        }
        if (!hasMagicBytes(content)) {
            return ValidationResult.failure("zip 文件魔数不匹配，不是有效的 ZIP 格式");
        }
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(content))) {
            if (zis.getNextEntry() == null) {
                return ValidationResult.failure("zip 文件没有任何有效条目");
            }
            return ValidationResult.success();
        } catch (Exception e) {
            return ValidationResult.failure("zip 文件解析失败: " + e.getMessage());
        }
    }

    private boolean hasMagicBytes(byte[] content) {
        for (int i = 0; i < ZIP_MAGIC.length; i++) {
            if (content[i] != ZIP_MAGIC[i]) {
                return false;
            }
        }
        return true;
    }

    @Override
    public String getSupportedExtension() {
        return "zip";
    }
}
