# Taskrabbit

Command line utility for moving Celery task messages
in and out of RabbitMQ.

Features multiple storage backends, currently file-based
and Sqlite backends are implemented.

## Example

Included is a simple Celery application, featuring "add" and
"multiply" tasks.

Docker is required to run this example. We assume a posix environment.

1. For simplicity, create an alias to run Taskrabbit in a docker container:

   ```
   $ alias taskr='docker-compose run --rm app python message_drain.py'
   ```

1. Start the RabbitMQ container:

   ```
   $ docker-compose up -d rabbit
   ```

1. Populate the task queue

   ```
   $ make tasks
   ```

1. Now the fun starts. Let's drain the queue to local file storage:

   ```
   $ taskr --queue celery --store file drain

   INFO:root:Draining queue: <unbound Queue celery -> <unbound Exchange default(direct)> -> celery>
   ┌────────────────┬───────┐
   │ Task           │ Count │
   ╞════════════════╪═══════╡
   │ tasks.multiply │ 30    │
   ├────────────────┼───────┤
   │ tasks.add      │ 30    │
   └────────────────┴───────┘
   ```

   Taskrabbit's output actually looks nice in the terminal, but currently does not copy/paste very well.

   The `--store file` option specifies to use the local filesystem to store tasks.

   We receive a summary showing the tasks removed from the queue.

1. Inspect the file store:

   ```
   $ ls tasks | head
   0582c334-0003-4aa6-a961-192374b15b38
   06fba055-107c-4fa2-94ec-fb21f9ae4986
   0860267f-677d-4df0-8374-68bdcfe32fcb
   0bc28667-6ba6-4572-91f3-8f607e015206
   0c1ad174-2e6c-4e92-a4ab-81a38a44608a
   0cfde908-cb42-4138-b693-d6f5fb6fa5fd
   265bb2fb-1823-4def-8837-bfb686c74c4d
   2ba3d592-740c-40bc-b986-6323be2ad0cb
   2ee04407-994f-4c64-9339-dafa0557f86a
   342ef58a-74d0-42ca-a519-960bc8e45d0a
   ```

1. Let's take a look at one of the files:

   ```
   $ cat tasks/`ls tasks|head -n 1`

    {
      "headers": {
        "lang": "py",
        "task": "tasks.multiply",
        "id": "0582c334-0003-4aa6-a961-192374b15b38",
        "shadow": null,
        "eta": null,
        "expires": null,
        "group": null,
        "group_index": null,
        "retries": 0,
        "timelimit": [
          null,
          null
        ],
        "root_id": "0582c334-0003-4aa6-a961-192374b15b38",
        "parent_id": null,
        "argsrepr": "(3, 3)",
        "kwargsrepr": "{}",
        "origin": "gen1@846d778d8248"
      },
      "body": [
        [
          3,
          3
        ],
        {},
        {
          "callbacks": null,
          "errbacks": null,
          "chain": null,
          "chord": null
        }
      ]
    }
   ```

1. We can also list the tasks with Taskrabbit:

   ```
   $ taskr --store file list

   ┌──────────────────────────────────────┬────────────────┬──────────┬────────┐
   │ ID                                   │ Task           │ Args     │ Kwargs │
   ╞══════════════════════════════════════╪════════════════╪══════════╪════════╡
   │ a82aca43-7d52-4c04-acf2-89febfa4a264 │ tasks.multiply │ (1, 1)   │ {}     │
   ├──────────────────────────────────────┼────────────────┼──────────┼────────┤
   │ 0582c334-0003-4aa6-a961-192374b15b38 │ tasks.multiply │ (3, 3)   │ {}     │
   ├──────────────────────────────────────┼────────────────┼──────────┼────────┤
   │ f7191978-f015-404d-bb8f-bacb3095b698 │ tasks.multiply │ (19, 19) │ {}     │
   ├──────────────────────────────────────┼────────────────┼──────────┼────────┤
   │ 0c1ad174-2e6c-4e92-a4ab-81a38a44608a │ tasks.add      │ (5, 5)   │ {}     │
   ├──────────────────────────────────────┼────────────────┼──────────┼────────┤

   <<< snip >>>
   │ 342ef58a-74d0-42ca-a519-960bc8e45d0a │ tasks.add      │ (13, 13) │ {}     │
   ├──────────────────────────────────────┼────────────────┼──────────┼────────┤
   │ 5fa73d53-7733-4aff-9152-877052021e81 │ tasks.add      │ (19, 19) │ {}     │
   └──────────────────────────────────────┴────────────────┴──────────┴────────┘
   ```

1. When we're ready, put the tasks back on the queue. Let's queue the add tasks first:

   ```
   $ taskr --store file fill --task tasks.add

   ┌───────────┬───────┐
   │ Task      │ Count │
   ╞═══════════╪═══════╡
   │ tasks.add │ 30    │
   └───────────┴───────┘
   ```

1. If we inspect the local store again, we should see only multiplication tasks:

   ```
   $ taskr --store file list --counts

   ┌────────────────┬───────┐
   │ Task           │ Count │
   ╞════════════════╪═══════╡
   │ tasks.multiply │ 30    │
   └────────────────┴───────┘
   ```

1. Let's put all the remaining tasks back on the queue:

   ```
   $ taskr --store file fill

   ┌────────────────┬───────┐
   │ Task           │ Count │
   ╞════════════════╪═══════╡
   │ tasks.multiply │ 30    │
   └────────────────┴───────┘
   ```

1. Finally, let's start a Celery worker to process our tasks:

   ```
   $ make worker

   worker_1  |  -------------- celery@4aadea6c83d9 v4.4.7 (cliffs)
   worker_1  | --- ***** -----
   worker_1  | -- ******* ---- Linux-4.19.104-microsoft-standard-x86_64-with-glibc2.2.5 2020-11-30 14:05:54
   worker_1  | - *** --- * ---
   worker_1  | - ** ---------- [config]
   worker_1  | - ** ---------- .> app:         celeryapp:0x7f98392ea310
   worker_1  | - ** ---------- .> transport:   amqp://guest:**@rabbit:5672//
   worker_1  | - ** ---------- .> results:     disabled://
   worker_1  | - *** --- * --- .> concurrency: 24 (prefork)
   worker_1  | -- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
   worker_1  | --- ***** -----
   worker_1  |  -------------- [queues]
   worker_1  |                 .> celery           exchange=celery(direct) key=celery
   worker_1  |
   worker_1  |
   worker_1  | [tasks]
   worker_1  |   . tasks.add
   worker_1  |   . tasks.multiply
   worker_1  |
   worker_1  | [2020-11-30 14:05:54,927: INFO/MainProcess] Connected to amqp://guest:**@rabbit:5672//
   worker_1  | [2020-11-30 14:05:54,935: INFO/MainProcess] mingle: searching for neighbors
   worker_1  | [2020-11-30 14:05:55,957: INFO/MainProcess] mingle: all alone
   worker_1  | [2020-11-30 14:05:55,973: INFO/MainProcess] celery@4aadea6c83d9 ready.
   worker_1  | [2020-11-30 14:05:55,974: INFO/MainProcess] Received task: tasks.add[0c1ad174-2e6c-4e92-a4ab-81a38a44608a]
   worker_1  | [2020-11-30 14:05:55,974: INFO/MainProcess] Received task: tasks.add[06fba055-107c-4fa2-94ec-fb21f9ae4986]
   worker_1  | [2020-11-30 14:05:55,975: INFO/MainProcess] Received task: tasks.add[f90dfa36-3fcd-44cb-b49c-3b02567d0a3d]
   worker_1  | [2020-11-30 14:05:55,975: INFO/MainProcess] Received task: tasks.add[53d5af73-9fa5-48fb-ba88-ac113a23c8a8]
   worker_1  | [2020-11-30 14:05:55,975: INFO/MainProcess] Received task: tasks.add[7b23acc2-a92b-40b5-831c-0642e36883fd]
   worker_1  | [2020-11-30 14:05:55,976: INFO/MainProcess] Received task: tasks.add[55972493-80d0-4dcb-ab53-b59561074be6]
   worker_1  | [2020-11-30 14:05:55,976: INFO/MainProcess] Received task: tasks.add[6198f981-05ce-442c-879d-f40eb7e3de81]
   worker_1  | [2020-11-30 14:05:55,976: INFO/MainProcess] Received task: tasks.add[5422e0ba-d211-4a7f-9e5d-dd844e82c833]
   worker_1  | [2020-11-30 14:05:55,976: INFO/MainProcess] Received task: tasks.add[dba8596f-74c5-4bfa-998a-84c008e8f007]
   worker_1  | [2020-11-30 14:05:55,977: INFO/MainProcess] Received task: tasks.add[fd4b852f-6a0c-4378-af5a-f23878a0f9b3]
   worker_1  | [2020-11-30 14:05:55,977: INFO/MainProcess] Received task: tasks.add[39d9c886-3204-4994-bdcc-fdefba94cbd4]
   worker_1  | [2020-11-30 14:05:55,977: INFO/MainProcess] Received task: tasks.add[50726b8d-c831-46fc-86aa-38e1c8156ddf]
   worker_1  | [2020-11-30 14:05:55,977: INFO/MainProcess] Received task: tasks.add[a1ad915d-580b-426a-8bb5-06b4b25b9905]
   worker_1  | [2020-11-30 14:05:55,978: INFO/MainProcess] Received task: tasks.add[40f9d26d-05e9-426b-bd35-8d15d19d881d]
   worker_1  | [2020-11-30 14:05:55,978: INFO/MainProcess] Received task: tasks.add[733697c0-2637-4213-99c4-f02ce3795746]
   worker_1  | [2020-11-30 14:05:55,978: INFO/MainProcess] Received task: tasks.add[7a7f9275-7900-46c5-88e5-a5f89089b53c]
   worker_1  | [2020-11-30 14:05:55,979: INFO/MainProcess] Received task: tasks.add[53118a18-209b-4db2-9b7b-4319300cbb03]
   worker_1  | [2020-11-30 14:05:55,979: INFO/MainProcess] Received task: tasks.add[c92130bf-be98-4490-acb6-a205c20db950]
   worker_1  | [2020-11-30 14:05:55,979: INFO/MainProcess] Received task: tasks.add[0bc28667-6ba6-4572-91f3-8f607e015206]
   worker_1  | [2020-11-30 14:05:55,979: INFO/MainProcess] Received task: tasks.add[8729c3c8-7204-4162-a264-c1738bfd90d6]
   worker_1  | [2020-11-30 14:05:55,980: INFO/MainProcess] Received task: tasks.add[af5dd5c7-d327-4468-8f5f-582a4e547e23]
   worker_1  | [2020-11-30 14:05:55,980: INFO/MainProcess] Received task: tasks.add[0cfde908-cb42-4138-b693-d6f5fb6fa5fd]
   worker_1  | [2020-11-30 14:05:55,980: INFO/MainProcess] Received task: tasks.add[878d764f-42ef-4356-82c1-3a6b9f086ca6]
   worker_1  | [2020-11-30 14:05:55,981: INFO/MainProcess] Received task: tasks.add[3c210e86-1d87-49ab-bd3b-47252092ff8e]
   worker_1  | [2020-11-30 14:05:55,981: INFO/MainProcess] Received task: tasks.add[b021276b-8515-478e-9d88-7aa9533740c1]
   worker_1  | [2020-11-30 14:05:55,981: INFO/MainProcess] Received task: tasks.add[6132ab61-f81d-461f-b1dc-7e1abfffc546]
   worker_1  | [2020-11-30 14:05:55,981: INFO/MainProcess] Received task: tasks.add[5662df6d-06b4-4532-b931-a16f8e825ba6]
   worker_1  | [2020-11-30 14:05:55,981: INFO/MainProcess] Received task: tasks.add[d8cf0322-5a70-4632-9441-98e6c181d575]
   worker_1  | [2020-11-30 14:05:55,982: INFO/MainProcess] Received task: tasks.add[342ef58a-74d0-42ca-a519-960bc8e45d0a]
   worker_1  | [2020-11-30 14:05:55,982: INFO/MainProcess] Received task: tasks.add[5fa73d53-7733-4aff-9152-877052021e81]
   worker_1  | [2020-11-30 14:05:55,982: INFO/MainProcess] Received task: tasks.multiply[a82aca43-7d52-4c04-acf2-89febfa4a264]
   worker_1  | [2020-11-30 14:05:55,982: INFO/MainProcess] Received task: tasks.multiply[0582c334-0003-4aa6-a961-192374b15b38]
   worker_1  | [2020-11-30 14:05:55,983: INFO/MainProcess] Received task: tasks.multiply[f7191978-f015-404d-bb8f-bacb3095b698]
   worker_1  | [2020-11-30 14:05:55,983: INFO/MainProcess] Received task: tasks.multiply[fd778bb1-0315-40f2-8847-5e0f11de9f21]
   worker_1  | [2020-11-30 14:05:55,983: INFO/MainProcess] Received task: tasks.multiply[eb8e3f29-c91c-4aa7-bd7d-11a70e695589]
   worker_1  | [2020-11-30 14:05:55,983: INFO/MainProcess] Received task: tasks.multiply[caf11c59-dbd1-4f88-bf37-1eaa08e28acb]
   worker_1  | [2020-11-30 14:05:55,984: INFO/MainProcess] Received task: tasks.multiply[5d8f0169-f418-47c0-96a6-5e7159d27be5]
   worker_1  | [2020-11-30 14:05:55,984: INFO/MainProcess] Received task: tasks.multiply[f6a930b8-ac26-498b-98dd-c3d8aff7985a]
   worker_1  | [2020-11-30 14:05:55,984: INFO/MainProcess] Received task: tasks.multiply[4217e0b5-ca05-4716-915e-4831fd034961]
   worker_1  | [2020-11-30 14:05:55,984: INFO/MainProcess] Received task: tasks.multiply[2ee04407-994f-4c64-9339-dafa0557f86a]
   worker_1  | [2020-11-30 14:05:55,985: INFO/MainProcess] Received task: tasks.multiply[bafbad02-e049-425d-b99d-f872abde7edb]
   worker_1  | [2020-11-30 14:05:55,985: INFO/MainProcess] Received task: tasks.multiply[62a03568-8322-4148-910e-539a63094b9b]
   worker_1  | [2020-11-30 14:05:55,985: INFO/MainProcess] Received task: tasks.multiply[0860267f-677d-4df0-8374-68bdcfe32fcb]
   worker_1  | [2020-11-30 14:05:55,985: INFO/MainProcess] Received task: tasks.multiply[e9cd61fe-5c71-4753-8d61-5577851dd911]
   worker_1  | [2020-11-30 14:05:55,985: INFO/MainProcess] Received task: tasks.multiply[8f01e7ee-d451-41ce-8fa0-3894149eadea]
   worker_1  | [2020-11-30 14:05:55,986: INFO/MainProcess] Received task: tasks.multiply[7ee72d81-7ac8-4c61-a3fc-6101693de0a2]
   worker_1  | [2020-11-30 14:05:55,986: INFO/MainProcess] Received task: tasks.multiply[aaf39d5d-a223-4b3e-96fa-f0085f8edd59]
   worker_1  | [2020-11-30 14:05:55,986: INFO/MainProcess] Received task: tasks.multiply[c949cb8b-06fc-4b7d-9dfe-153e06385b57]
   worker_1  | [2020-11-30 14:05:55,986: INFO/MainProcess] Received task: tasks.multiply[93d40116-ad2c-4b65-8356-5b241bba2089]
   worker_1  | [2020-11-30 14:05:55,987: INFO/MainProcess] Received task: tasks.multiply[3c099b6f-e73f-44cc-ba50-5ff41dfb9014]
   worker_1  | [2020-11-30 14:05:55,987: INFO/MainProcess] Received task: tasks.multiply[2ba3d592-740c-40bc-b986-6323be2ad0cb]
   worker_1  | [2020-11-30 14:05:55,987: INFO/MainProcess] Received task: tasks.multiply[265bb2fb-1823-4def-8837-bfb686c74c4d]
   worker_1  | [2020-11-30 14:05:55,987: INFO/MainProcess] Received task: tasks.multiply[76deea05-4c50-42fc-bcb6-eafefc36d938]
   worker_1  | [2020-11-30 14:05:55,988: INFO/MainProcess] Received task: tasks.multiply[606e1087-30e1-4809-aefd-3b16c5388a2d]
   worker_1  | [2020-11-30 14:05:55,988: INFO/MainProcess] Received task: tasks.multiply[6fe56fe0-3c08-41ad-b13e-2d117d3a6f40]
   worker_1  | [2020-11-30 14:05:55,988: INFO/MainProcess] Received task: tasks.multiply[89e3f984-9e2d-4716-b99c-8b0f239e5bf6]
   worker_1  | [2020-11-30 14:05:55,988: INFO/MainProcess] Received task: tasks.multiply[970c297b-0cd6-4e12-beba-f9c40c003af5]
   worker_1  | [2020-11-30 14:05:55,988: INFO/MainProcess] Received task: tasks.multiply[f4f498c1-da40-4919-9e16-792cadf8ee6d]
   worker_1  | [2020-11-30 14:05:55,989: INFO/MainProcess] Received task: tasks.multiply[dec05118-a50c-47b6-b9d3-978beaaf4f45]
   worker_1  | [2020-11-30 14:05:55,989: INFO/MainProcess] Received task: tasks.multiply[4dad5a08-ed29-4681-87c2-7d9f4735afc0]
   worker_1  | [2020-11-30 14:05:56,091: INFO/ForkPoolWorker-2] Task tasks.add[53d5af73-9fa5-48fb-ba88-ac113a23c8a8] succeeded in 0.0002207000507041812s: 8
   worker_1  | [2020-11-30 14:05:56,091: INFO/ForkPoolWorker-19] Task tasks.add[6198f981-05ce-442c-879d-f40eb7e3de81] succeeded in 0.00016280007548630238s: 6
   worker_1  | [2020-11-30 14:05:56,092: INFO/ForkPoolWorker-3] Task tasks.add[55972493-80d0-4dcb-ab53-b59561074be6] succeeded in 0.00013770000077784061s: 20
   worker_1  | [2020-11-30 14:05:56,093: INFO/ForkPoolWorker-13] Task tasks.add[0cfde908-cb42-4138-b693-d6f5fb6fa5fd] succeeded in 0.00014610006473958492s: 58
   worker_1  | [2020-11-30 14:05:56,091: INFO/ForkPoolWorker-18] Task tasks.add[7b23acc2-a92b-40b5-831c-0642e36883fd] succeeded in 0.00015710003208369017s: 32
   worker_1  | [2020-11-30 14:05:56,091: INFO/ForkPoolWorker-17] Task tasks.add[f90dfa36-3fcd-44cb-b49c-3b02567d0a3d] succeeded in 0.000161800067871809s: 44
   worker_1  | [2020-11-30 14:05:56,092: INFO/ForkPoolWorker-10] Task tasks.add[0bc28667-6ba6-4572-91f3-8f607e015206] succeeded in 0.00012869993224740028s: 36
   worker_1  | [2020-11-30 14:05:56,091: INFO/ForkPoolWorker-1] Task tasks.add[06fba055-107c-4fa2-94ec-fb21f9ae4986] succeeded in 0.00020499993115663528s: 56
   worker_1  | [2020-11-30 14:05:56,092: INFO/ForkPoolWorker-9] Task tasks.add[c92130bf-be98-4490-acb6-a205c20db950] succeeded in 0.00013589998707175255s: 0
   worker_1  | [2020-11-30 14:05:56,092: INFO/ForkPoolWorker-12] Task tasks.add[af5dd5c7-d327-4468-8f5f-582a4e547e23] succeeded in 0.00016030005645006895s: 40
   worker_1  | [2020-11-30 14:05:56,093: INFO/ForkPoolWorker-7] Task tasks.add[40f9d26d-05e9-426b-bd35-8d15d19d881d] succeeded in 0.00012260000221431255s: 24
   worker_1  | [2020-11-30 14:05:56,091: INFO/ForkPoolWorker-16] Task tasks.add[0c1ad174-2e6c-4e92-a4ab-81a38a44608a] succeeded in 0.00012589991092681885s: 10
   worker_1  | [2020-11-30 14:05:56,094: INFO/ForkPoolWorker-5] Task tasks.add[fd4b852f-6a0c-4378-af5a-f23878a0f9b3] succeeded in 0.002625899971462786s: 16
   worker_1  | [2020-11-30 14:05:56,092: INFO/ForkPoolWorker-11] Task tasks.add[8729c3c8-7204-4162-a264-c1738bfd90d6] succeeded in 0.00025509996339678764s: 14
   worker_1  | [2020-11-30 14:05:56,094: INFO/ForkPoolWorker-20] Task tasks.add[dba8596f-74c5-4bfa-998a-84c008e8f007] succeeded in 0.00291719997767359s: 48
   worker_1  | [2020-11-30 14:05:56,094: INFO/ForkPoolWorker-4] Task tasks.add[5422e0ba-d211-4a7f-9e5d-dd844e82c833] succeeded in 0.002948799985460937s: 50
   worker_1  | [2020-11-30 14:05:56,092: INFO/ForkPoolWorker-8] Task tasks.add[7a7f9275-7900-46c5-88e5-a5f89089b53c] succeeded in 0.0001466000685468316s: 34
   worker_1  | [2020-11-30 14:05:56,091: INFO/ForkPoolWorker-21] Task tasks.add[39d9c886-3204-4994-bdcc-fdefba94cbd4] succeeded in 0.00015919993165880442s: 54
   worker_1  | [2020-11-30 14:05:56,094: INFO/ForkPoolWorker-24] Task tasks.add[53118a18-209b-4db2-9b7b-4319300cbb03] succeeded in 0.0026883999817073345s: 42
   worker_1  | [2020-11-30 14:05:56,094: INFO/ForkPoolWorker-15] Task tasks.add[3c210e86-1d87-49ab-bd3b-47252092ff8e] succeeded in 0.00014709995593875647s: 52
   worker_1  | [2020-11-30 14:05:56,094: INFO/ForkPoolWorker-6] Task tasks.add[50726b8d-c831-46fc-86aa-38e1c8156ddf] succeeded in 0.00293810002040118s: 28
   worker_1  | [2020-11-30 14:05:56,094: INFO/ForkPoolWorker-22] Task tasks.add[a1ad915d-580b-426a-8bb5-06b4b25b9905] succeeded in 0.0001919000642374158s: 30
   worker_1  | [2020-11-30 14:05:56,095: INFO/ForkPoolWorker-14] Task tasks.add[878d764f-42ef-4356-82c1-3a6b9f086ca6] succeeded in 0.0001732000382617116s: 18
   worker_1  | [2020-11-30 14:05:56,095: INFO/ForkPoolWorker-23] Task tasks.add[733697c0-2637-4213-99c4-f02ce3795746] succeeded in 0.00017629994545131922s: 22
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-16] Task tasks.add[b021276b-8515-478e-9d88-7aa9533740c1] succeeded in 7.289997301995754e-05s: 4
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-1] Task tasks.add[6132ab61-f81d-461f-b1dc-7e1abfffc546] succeeded in 4.819990135729313e-05s: 46
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-17] Task tasks.add[5662df6d-06b4-4532-b931-a16f8e825ba6] succeeded in 4.39999857917428e-05s: 12
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-2] Task tasks.add[d8cf0322-5a70-4632-9441-98e6c181d575] succeeded in 5.170004442334175e-05s: 2
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-3] Task tasks.add[5fa73d53-7733-4aff-9152-877052021e81] succeeded in 3.529991954565048e-05s: 38
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-18] Task tasks.add[342ef58a-74d0-42ca-a519-960bc8e45d0a] succeeded in 5.2900053560733795e-05s: 26
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-19] Task tasks.multiply[a82aca43-7d52-4c04-acf2-89febfa4a264] succeeded in 4.269997589290142e-05s: 1
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-5] Task tasks.multiply[fd778bb1-0315-40f2-8847-5e0f11de9f21] succeeded in 3.8499943912029266e-05s: 144
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-4] Task tasks.multiply[0582c334-0003-4aa6-a961-192374b15b38] succeeded in 5.789997521787882e-05s: 9
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-20] Task tasks.multiply[f7191978-f015-404d-bb8f-bacb3095b698] succeeded in 5.45999500900507e-05s: 361
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-21] Task tasks.multiply[eb8e3f29-c91c-4aa7-bd7d-11a70e695589] succeeded in 5.030003376305103e-05s: 25
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-6] Task tasks.multiply[caf11c59-dbd1-4f88-bf37-1eaa08e28acb] succeeded in 8.140003774315119e-05s: 169
   worker_1  | [2020-11-30 14:05:56,097: INFO/ForkPoolWorker-22] Task tasks.multiply[5d8f0169-f418-47c0-96a6-5e7159d27be5] succeeded in 7.209996692836285e-05s: 4
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-23] Task tasks.multiply[4217e0b5-ca05-4716-915e-4831fd034961] succeeded in 4.47999918833375e-05s: 100
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-7] Task tasks.multiply[f6a930b8-ac26-498b-98dd-c3d8aff7985a] succeeded in 6.079999729990959e-05s: 289
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-8] Task tasks.multiply[2ee04407-994f-4c64-9339-dafa0557f86a] succeeded in 5.959998816251755e-05s: 576
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-24] Task tasks.multiply[bafbad02-e049-425d-b99d-f872abde7edb] succeeded in 6.059999577701092e-05s: 121
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-10] Task tasks.multiply[0860267f-677d-4df0-8374-68bdcfe32fcb] succeeded in 5.540007259696722e-05s: 225
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-9] Task tasks.multiply[62a03568-8322-4148-910e-539a63094b9b] succeeded in 6.10999995842576e-05s: 81
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-12] Task tasks.multiply[8f01e7ee-d451-41ce-8fa0-3894149eadea] succeeded in 8.490006439387798e-05s: 676
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-11] Task tasks.multiply[e9cd61fe-5c71-4753-8d61-5577851dd911] succeeded in 8.41999426484108e-05s: 324
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-14] Task tasks.multiply[aaf39d5d-a223-4b3e-96fa-f0085f8edd59] succeeded in 7.16999638825655e-05s: 196
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-13] Task tasks.multiply[7ee72d81-7ac8-4c61-a3fc-6101693de0a2] succeeded in 8.000002708286047e-05s: 36
   worker_1  | [2020-11-30 14:05:56,098: INFO/ForkPoolWorker-15] Task tasks.multiply[c949cb8b-06fc-4b7d-9dfe-153e06385b57] succeeded in 8.059991523623466e-05s: 729
   worker_1  | [2020-11-30 14:05:56,101: INFO/ForkPoolWorker-16] Task tasks.multiply[93d40116-ad2c-4b65-8356-5b241bba2089] succeeded in 9.539991151541471e-05s: 441
   worker_1  | [2020-11-30 14:05:56,101: INFO/ForkPoolWorker-1] Task tasks.multiply[3c099b6f-e73f-44cc-ba50-5ff41dfb9014] succeeded in 0.00010960001964122057s: 841
   worker_1  | [2020-11-30 14:05:56,101: INFO/ForkPoolWorker-17] Task tasks.multiply[2ba3d592-740c-40bc-b986-6323be2ad0cb] succeeded in 5.619996227324009e-05s: 400
   worker_1  | [2020-11-30 14:05:56,101: INFO/ForkPoolWorker-18] Task tasks.multiply[76deea05-4c50-42fc-bcb6-eafefc36d938] succeeded in 5.4900068789720535e-05s: 484
   worker_1  | [2020-11-30 14:05:56,101: INFO/ForkPoolWorker-2] Task tasks.multiply[265bb2fb-1823-4def-8837-bfb686c74c4d] succeeded in 6.0699996538460255e-05s: 256
   worker_1  | [2020-11-30 14:05:56,101: INFO/ForkPoolWorker-3] Task tasks.multiply[606e1087-30e1-4809-aefd-3b16c5388a2d] succeeded in 5.0600036047399044e-05s: 0
   worker_1  | [2020-11-30 14:05:56,101: INFO/ForkPoolWorker-19] Task tasks.multiply[6fe56fe0-3c08-41ad-b13e-2d117d3a6f40] succeeded in 4.1599967516958714e-05s: 64
   worker_1  | [2020-11-30 14:05:56,102: INFO/ForkPoolWorker-4] Task tasks.multiply[89e3f984-9e2d-4716-b99c-8b0f239e5bf6] succeeded in 5.519995465874672e-05s: 784
   worker_1  | [2020-11-30 14:05:56,102: INFO/ForkPoolWorker-20] Task tasks.multiply[970c297b-0cd6-4e12-beba-f9c40c003af5] succeeded in 6.54000323265791e-05s: 49
   worker_1  | [2020-11-30 14:05:56,102: INFO/ForkPoolWorker-6] Task tasks.multiply[4dad5a08-ed29-4681-87c2-7d9f4735afc0] succeeded in 6.640003994107246e-05s: 529
   worker_1  | [2020-11-30 14:05:56,102: INFO/ForkPoolWorker-5] Task tasks.multiply[f4f498c1-da40-4919-9e16-792cadf8ee6d] succeeded in 7.379997987300158e-05s: 16
   worker_1  | [2020-11-30 14:05:56,102: INFO/ForkPoolWorker-21] Task tasks.multiply[dec05118-a50c-47b6-b9d3-978beaaf4f45] succeeded in 8.619995787739754e-05s: 625
   ```

   (Stop the worker with `Ctrl+C`)

   You can see that our task messages have survived the trip through our local file system.
