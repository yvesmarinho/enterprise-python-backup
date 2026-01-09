#!/bin/bash
# COPILOT FILE CREATION ENFORCEMENT CHECKLIST
# This script serves as documentation for the MANDATORY file creation rules
# Status: ENFORCED - NO EXCEPTIONS - ALL SESSIONS

# 🔴 FORBIDDEN PATTERNS (NEVER USE):
#
# cat <<EOF > file.txt         ❌ HEREDOC - FORBIDDEN
#   content
# EOF
#
# echo "text" > file.txt       ❌ ECHO REDIRECT - FORBIDDEN
# echo "text" | tee file.txt   ❌ ECHO PIPE - FORBIDDEN
# printf "x" | cat > file      ❌ PRINTF PIPE - FORBIDDEN
# cat file1 > file2            ❌ CAT COPY - FORBIDDEN (use cp)
#
# ANY combination of the above  ❌ FORBIDDEN

# ✅ CORRECT PATTERN (MANDATORY - 3 STEPS):
#
# Step 1: CREATE
#   create_file /path/to/file "COMPLETE FILE CONTENT"
#
# Step 2: DISPLAY
#   cat /path/to/file
#
# Step 3: CLEANUP (if temporary)
#   rm /path/to/file

# ================================================================================
# DECISION TREE
# ================================================================================

# Q: Need to create a file?
# A: Use create_file tool - PERIOD.

# Q: Need to create a temporary file, display, and delete?
# A: 1. create_file
#    2. cat
#    3. rm

# Q: Need to edit an existing file?
# A: Use replace_string_in_file tool

# Q: Should I use cat <<EOF?
# A: NO. Use create_file tool instead.

# Q: Should I use echo > file?
# A: NO. Use create_file tool instead.

# Q: What if I need to pipe commands?
# A: Separate operations:
#    1. create_file /tmp/script.sh "content"
#    2. bash /tmp/script.sh
#    3. rm /tmp/script.sh

# ================================================================================
# ENFORCEMENT MATRIX
# ================================================================================

# TASK                              | CORRECT              | WRONG
# ---|---|---
# Create configuration file         | create_file          | echo > / cat <<EOF
# Create script                      | create_file          | echo > / cat <<EOF
# Create manifest (k8s, docker)     | create_file          | echo > / cat <<EOF
# Create documentation              | create_file          | echo > / cat <<EOF
# Create temporary display file     | create_file + rm     | cat <<EOF
# Display file                      | cat / read_file      | cat <<EOF
# Edit existing file               | replace_string_in    | echo >>
# Delete file                      | rm in terminal       | cat /dev/null >

# ================================================================================
# VERIFICATION CHECKLIST
# ================================================================================

# BEFORE any file operation, answer YES to all:
#
# [1] Am I using create_file tool to create?        ✅
# [2] Is the file content COMPLETE in the call?     ✅
# [3] Will I display the file after creation?       ✅
# [4] Will I cleanup temp files with rm?            ✅
# [5] NO echo/cat/printf/heredoc involved?          ✅
# [6] Would this work in CI/CD pipeline?            ✅
#
# If ANY answer is NO, STOP and reconsider the approach.

# ================================================================================
# EXAMPLES
# ================================================================================

# Example 1: Create & Display Configuration
# Step 1: create_file /etc/app.conf "key1=value1
# key2=value2"
# Step 2: cat /etc/app.conf
# ✅ CORRECT | ❌ NOT: echo "key1=value1" > /etc/app.conf

# Example 2: Create, Display & Cleanup Script
# Step 1: create_file /tmp/deploy.sh "#!/bin/bash
# echo 'Deploying...'"
# Step 2: cat /tmp/deploy.sh
# Step 3: bash /tmp/deploy.sh
# Step 4: rm /tmp/deploy.sh
# ✅ CORRECT | ❌ NOT: cat <<EOF > /tmp/deploy.sh

# Example 3: Create Kubernetes Manifest
# Step 1: create_file /tmp/pod.yaml "apiVersion: v1
# kind: Pod
# metadata:
#   name: test"
# Step 2: cat /tmp/pod.yaml
# Step 3: kubectl apply -f /tmp/pod.yaml
# Step 4: rm /tmp/pod.yaml
# ✅ CORRECT | ❌ NOT: cat <<EOF | kubectl apply -f -

# ================================================================================
# MANDATORY RULES
# ================================================================================

# Rule 1: NEVER use cat <<EOF for file creation
# Rule 2: NEVER use echo with > or >> for file creation
# Rule 3: NEVER use printf | with file operations
# Rule 4: ALWAYS use create_file tool for creating files
# Rule 5: ALWAYS display file with cat or read_file after creation
# Rule 6: ALWAYS cleanup temporary files with rm
# Rule 7: Use replace_string_in_file for editing existing files
# Rule 8: Use run_in_terminal for complex command sequences
#
# Enforcement Level: 🔴 100% MANDATORY - ZERO EXCEPTIONS
# Applies To: ALL Copilot file operations
# Date: 2025-11-26
# Status: ACTIVE & ENFORCED

# ================================================================================
# RATIONALE
# ================================================================================

# WHY use create_file instead of cat <<EOF?
#
# 1. Copilot has FULL file manipulation permissions
#    → No need for shell workarounds
#
# 2. create_file is simpler and more reliable
#    → No escaping issues, no shell interpretation
#
# 3. Better audit trail
#    → Easy to track what files were created
#
# 4. Works in CI/CD pipelines
#    → More reproducible and maintainable
#
# 5. Professional standards
#    → Industry best practices
#
# 6. No special character issues
#    → Handles quotes, newlines, etc. safely
#
# 7. Consistent behavior
#    → Same result every time, every environment

# ================================================================================
# END OF ENFORCEMENT DOCUMENTATION
# ================================================================================

echo "✅ COPILOT FILE CREATION RULES - LOADED"
echo "🔴 STATUS: MANDATORY - ENFORCED"
echo "📖 READ: .copilot-strict-rules.md"
echo "⚡ QUICK: docs/COPILOT_FILE_MANIPULATION_QUICK_REFERENCE.md"
