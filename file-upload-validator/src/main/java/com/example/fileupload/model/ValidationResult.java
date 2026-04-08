package com.example.fileupload.model;

/**
 * 文件校验结果
 */
public class ValidationResult {
    private final boolean valid;
    private final String message;

    private ValidationResult(boolean valid, String message) {
        this.valid = valid;
        this.message = message;
    }

    public static ValidationResult success() {
        return new ValidationResult(true, "校验通过");
    }

    public static ValidationResult failure(String message) {
        return new ValidationResult(false, message);
    }

    public boolean isValid() {
        return valid;
    }

    public String getMessage() {
        return message;
    }

    @Override
    public String toString() {
        return "ValidationResult{valid=" + valid + ", message='" + message + "'}";
    }
}
