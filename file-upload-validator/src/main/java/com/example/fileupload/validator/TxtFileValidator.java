package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CharsetDecoder;
import java.nio.charset.StandardCharsets;

/**
 * TXT 文件校验器：内容必须是合法的 UTF-8 或 GBK 文本，且不能为空
 */
public class TxtFileValidator implements FileValidator {

    @Override
    public ValidationResult validate(byte[] content, String filename) {
        if (content == null || content.length == 0) {
            return ValidationResult.failure("txt 文件内容不能为空");
        }
        // 优先尝试 UTF-8，再尝试 GBK
        if (isDecodable(content, StandardCharsets.UTF_8)) {
            return ValidationResult.success();
        }
        if (isDecodable(content, Charset.forName("GBK"))) {
            return ValidationResult.success();
        }
        return ValidationResult.failure("txt 文件内容不是合法的文本编码（UTF-8/GBK）");
    }

    private boolean isDecodable(byte[] content, Charset charset) {
        CharsetDecoder decoder = charset.newDecoder();
        try {
            decoder.decode(ByteBuffer.wrap(content));
            return true;
        } catch (CharacterCodingException e) {
            return false;
        }
    }

    @Override
    public String getSupportedExtension() {
        return "txt";
    }
}
