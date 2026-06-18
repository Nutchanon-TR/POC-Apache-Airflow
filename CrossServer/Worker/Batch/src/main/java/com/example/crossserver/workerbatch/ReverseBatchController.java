package com.example.crossserver.workerbatch;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import org.springframework.batch.core.BatchStatus;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.http.HttpStatus;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class ReverseBatchController {

    private final JobLauncher jobLauncher;
    private final Job reverseTextJob;
    private final ReverseBatchProperties properties;
    private final AzureBlobService azureBlobService;

    public ReverseBatchController(
            JobLauncher jobLauncher,
            Job reverseTextJob,
            ReverseBatchProperties properties,
            AzureBlobService azureBlobService) {
        this.jobLauncher = jobLauncher;
        this.reverseTextJob = reverseTextJob;
        this.properties = properties;
        this.azureBlobService = azureBlobService;
    }

    @GetMapping("/batch/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }

    @PostMapping("/batch/reverse")
    public ReverseResponse reverse(@RequestBody(required = false) ReverseRequest request) throws Exception {
        ReverseRequest safeRequest = request == null ? new ReverseRequest(null, null) : request;
        String inputPath = StringUtils.hasText(safeRequest.inputPath())
                ? safeRequest.inputPath()
                : properties.getDefaultInputPath();
        String outputPath = StringUtils.hasText(safeRequest.outputPath())
                ? safeRequest.outputPath()
                : properties.getDefaultOutputPath();

        JobParameters parameters = new JobParametersBuilder()
                .addString("inputPath", inputPath)
                .addString("outputPath", outputPath)
                .addLong("requestedAt", System.currentTimeMillis())
                .toJobParameters();

        JobExecution execution = jobLauncher.run(reverseTextJob, parameters);
        if (execution.getStatus() != BatchStatus.COMPLETED) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "Reverse batch failed with status " + execution.getStatus());
        }

        long bytes = Files.size(Path.of(outputPath));
        String blobName = "ct2-out/" + Path.of(outputPath).getFileName();
        String blobUrl = azureBlobService.uploadIfConfigured(Path.of(outputPath), blobName);

        return new ReverseResponse(execution.getJobId(), execution.getStatus().toString(),
                inputPath, outputPath, bytes, blobUrl);
    }

    public record ReverseRequest(String inputPath, String outputPath) {
    }

    public record ReverseResponse(
            Long jobId, String status,
            String inputPath, String outputPath,
            long bytes, String blobUrl) {
    }
}
