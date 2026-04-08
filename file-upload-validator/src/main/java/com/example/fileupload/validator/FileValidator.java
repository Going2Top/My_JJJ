package com.example.fileupload.validator;

import com.example.fileupload.model.ValidationResult;

/**
 * 文件内容校验器接口
 */
public interface FileValidator {

    /**
     * 校验文件内容是否合法
     *
     * @param content  文件字节内容
     * @param filename 文件名（含扩展名）
     * @return 校验结果
     */
    ValidationResult validate(byte[] content, String filename);

    /**
     * 该校验器支持的文件扩展名（小写，不含点），例如 "txt"
     */
    String getSupportedExtension();
}
