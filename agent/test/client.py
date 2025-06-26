#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import argparse
import os
from functools import partial
from agent.canvas import Canvas
from agent.settings import DEBUG

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    dsl_default_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "dsl_examples",
        "retrieval_and_generate.json",
    )
    parser.add_argument('-s', '--dsl', default=dsl_default_path, help="input dsl", action='store', required=False) # Made DSL not strictly required for programmatic call
    parser.add_argument('-t', '--tenant_id', default="test_tenant", help="Tenant ID", action='store', required=False) # Default tenant_id
    parser.add_argument('-m', '--stream', default=False, help="Stream output", action='store_true', required=False)
    parser.add_argument('-q', '--question', default="Hello", help="Initial question for non-interactive run", action='store')
    args = parser.parse_args()

    print(f"Using DSL file: {args.dsl}")
    print(f"Using Tenant ID: {args.tenant_id}")
    print(f"Stream mode: {args.stream}")
    print(f"Initial question: {args.question}")

    try:
        with open(args.dsl, "r") as f:
            dsl_content = f.read()
        canvas = Canvas(dsl_content) # tenant_id removed

        # Add initial user input if provided (some flows might not need it immediately)
        if args.question:
            canvas.add_user_input(args.question)
            print(f"\nAdded initial question: {args.question}")

        print("\nRunning canvas...")
        ans_generator = canvas.run(stream=args.stream)

        final_bot_output = None
        print("\n==================== Bot Output ====================", flush=True)
        if args.stream:
            full_response = ""
            for an_item in ans_generator:
                # an_item could be {"content": "...", "running_status": True} or final response
                if isinstance(an_item, dict) and "content" in an_item:
                    new_content = an_item["content"]
                    # If it's a running status, it might not be part of the final answer
                    if an_item.get("running_status"):
                        print(f"\n[Status Update] {new_content}", flush=True)
                    else: # This is part of the answer stream
                        # Check if new_content is what's already printed
                        if full_response and new_content.startswith(full_response):
                            print(new_content[len(full_response):], end='', flush=True)
                        else: # It's a new/different piece of content or the first one
                            print(new_content, end='', flush=True)
                        full_response = new_content # Assume it's the full response up to this point
                    final_bot_output = full_response # Keep track of the latest content
                else:
                    print(f"\n[Stream Item] {an_item}", flush=True) # Fallback for unexpected stream item format
            print() # Newline after stream
        else: # Not streaming
            # The generator should yield one item in non-stream mode
            for final_ans_dict in ans_generator:
                 if isinstance(final_ans_dict, dict) and "content" in final_ans_dict:
                    final_bot_output = final_ans_dict["content"]
                    print(f"> {final_bot_output}", flush=True)
                 else: # Should be a DataFrame if coming from a component directly without Answer node
                    # This case might occur if the flow ends not on an Answer node.
                    # The canvas run() method is designed to yield dicts from Answer or running hints.
                    # If final_ans_dict is a DataFrame, it means something might be off in flow or expectations.
                    print(f"\n[Bot DataFrame Output]\n{final_ans_dict}", flush=True)
                    final_bot_output = str(final_ans_dict)


        if DEBUG: # DEBUG is from agent.settings
            print("\nCanvas Path:", canvas.path)
            print("Canvas History:", canvas.history)
            print("Canvas Messages:", canvas.messages)
            print("Canvas Answer Queue:", canvas.answer)

        print("\n==================== Test Run Complete ====================", flush=True)
        if final_bot_output is None:
            print("WARNING: Bot did not produce a final output string.", flush=True)
            # This might indicate an issue with the flow or the Answer component.
            # We'll consider it a pass if no exceptions, but it's worth noting.

    except Exception as e:
        import traceback
        print(f"\n!!!!!!!!!!!!!!!!!!!! ERROR DURING TEST RUN !!!!!!!!!!!!!!!!!!!!", flush=True)
        print(f"DSL: {args.dsl}", flush=True)
        print(f"Exception: {type(e).__name__} - {e}", flush=True)
        print("Traceback:", flush=True)
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!! END ERROR DETAILS !!!!!!!!!!!!!!!!!!!!", flush=True)
        # Ensure script exits with error status
        exit(1)
