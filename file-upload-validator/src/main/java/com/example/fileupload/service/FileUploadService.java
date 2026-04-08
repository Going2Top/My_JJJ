package com.example.fileupload.service;

import com.example.fileupload.model.BatchUploadResult;
import com.example.fileupload.model.FileUploadRequest;
import com.example.fileupload.model.FileUploadResult;
import com.example.fileupload.model.ValidationResult;
import com.example.fileupload.remote.RemoteStorageService;
import com.example.fileupload.validator.FileValidator;
import com.example.fileupload.validator.FileValidatorFactory;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * 文件上传服务
 *
 * <p><b>流消费问题的解决方案：</b><br>
 * 上传时先将 InputStream 完整读入 byte[]，这样：
 * <ul>
 *   <li>校验阶段直接操作 byte[]，不消费原始流</li>
 *   <li>上传阶段用 {@code new ByteArrayInputStream(bytes)} 重建流，传给远端存储</li>
 * </ul>
 * 代价是文件内容会短暂驻留内存；对于超大文件可改用临时文件或 TeeInputStream 方案。
 * </p>
 */
public class FileUploadService {

    private final FileValidatorFactory validatorFactory;
    private final RemoteStorageService remoteStorage;

    public FileUploadService(RemoteStorageService remoteStorage) {
        this.validatorFactory = new FileValidatorFactory();
        this.remoteStorage = remoteStorage;
    }

    /**
     * 上传单个文件
     */
    public FileUploadResult upload(FileUploadRequest request) {
        String filename = request.getFilename();

        // ---- 关键步骤 1：一次性读取流到字节数组，解决流只能消费一次的问题 ----
        byte[] content;
        try {
            content = request.getInputStream().readAllBytes();
        } catch (IOException e) {
            return FileUploadResult.failure(filename, "读取文件流失败: " + e.getMessage());
        }

        // ---- 步骤 2：检查文件类型是否支持 ----
        if (!validatorFactory.isSupported(filename)) {
            return FileUploadResult.failure(filename, "不支持的文件类型，仅支持: txt, zip, properties, sql, yaml");
        }

        // ---- 步骤 3：内容校验（使用 byte[]，不消费流）----
        FileValidator validator = validatorFactory.getValidator(filename);
        ValidationResult validationResult = validator.validate(content, filename);
        if (!validationResult.isValid()) {
            return FileUploadResult.failure(filename, validationResult.getMessage());
        }

        // ---- 步骤 4：上传到远端（用 byte[] 重新构建流，原始流已消费也无影响）----
        try {
            String remotePath = remoteStorage.store(filename, new ByteArrayInputStream(content));
            return FileUploadResult.success(filename, remotePath);
        } catch (Exception e) {
            return FileUploadResult.failure(filename, "远端存储异常: " + e.getMessage());
        }
    }

    /**
     * 批量上传：逐个处理，任一文件失败不影响其他文件
     */
    public BatchUploadResult uploadBatch(List<FileUploadRequest> requests) {
        List<FileUploadResult> results = new ArrayList<>();
        for (FileUploadRequest request : requests) {
            results.add(upload(request));
        }
        return new BatchUploadResult(results);
    }
}
