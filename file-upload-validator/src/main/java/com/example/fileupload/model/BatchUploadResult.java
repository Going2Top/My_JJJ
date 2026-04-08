package com.example.fileupload.model;

import java.util.List;

/**
 * 批量上传结果汇总
 */
public class BatchUploadResult {
    private final List<FileUploadResult> results;
    private final int total;
    private final int successCount;
    private final int failCount;

    public BatchUploadResult(List<FileUploadResult> results) {
        this.results = results;
        this.total = results.size();
        this.successCount = (int) results.stream().filter(FileUploadResult::isSuccess).count();
        this.failCount = total - successCount;
    }

    public List<FileUploadResult> getResults() {
        return results;
    }

    public int getTotal() {
        return total;
    }

    public int getSuccessCount() {
        return successCount;
    }

    public int getFailCount() {
        return failCount;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("BatchUploadResult{total=").append(total)
          .append(", success=").append(successCount)
          .append(", fail=").append(failCount)
          .append("}\n");
        results.forEach(r -> sb.append("  ").append(r).append("\n"));
        return sb.toString();
    }
}
