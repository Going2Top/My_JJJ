package com.example.fileupload.model;

/**
 * 单个文件上传结果
 */
public class FileUploadResult {
    private final String filename;
    private final boolean success;
    private final String message;

    private FileUploadResult(String filename, boolean success, String message) {
        this.filename = filename;
        this.success = success;
        this.message = message;
    }

    public static FileUploadResult success(String filename, String remotePath) {
        return new FileUploadResult(filename, true, "上传成功，远端路径: " + remotePath);
    }

    public static FileUploadResult failure(String filename, String reason) {
        return new FileUploadResult(filename, false, "上传失败: " + reason);
    }

    public String getFilename() {
        return filename;
    }

    public boolean isSuccess() {
        return success;
    }

    public String getMessage() {
        return message;
    }

    @Override
    public String toString() {
        return "FileUploadResult{filename='" + filename + "', success=" + success + ", message='" + message + "'}";
    }
}
