package com.example.crossserver.workerbatch;

import java.nio.file.Path;

import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.configuration.annotation.StepScope;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.core.step.tasklet.Tasklet;
import org.springframework.batch.repeat.RepeatStatus;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.PlatformTransactionManager;

@Configuration
public class ReverseJobConfiguration {

    @Bean
    public Job reverseTextJob(JobRepository jobRepository, Step reverseTextStep) {
        return new JobBuilder("reverseTextJob", jobRepository)
                .start(reverseTextStep)
                .build();
    }

    @Bean
    public Step reverseTextStep(
            JobRepository jobRepository,
            PlatformTransactionManager transactionManager,
            Tasklet reverseTextTasklet
    ) {
        return new StepBuilder("reverseTextStep", jobRepository)
                .tasklet(reverseTextTasklet, transactionManager)
                .build();
    }

    @Bean
    @StepScope
    public Tasklet reverseTextTasklet(
            ReverseTextService reverseTextService,
            @Value("#{jobParameters['inputPath']}") String inputPath,
            @Value("#{jobParameters['outputPath']}") String outputPath
    ) {
        return (contribution, chunkContext) -> {
            reverseTextService.reverseText(Path.of(inputPath), Path.of(outputPath));
            return RepeatStatus.FINISHED;
        };
    }
}
